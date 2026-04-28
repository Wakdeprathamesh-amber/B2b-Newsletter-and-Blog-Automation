"""LangGraph pipeline definition for the Amber Content Engine.

This is the master graph that wires all stages together:

    Stage 1 (ingest) — 10-20 signals per region
        |
    Stage 2 (topic selection) — 30-50 ranked topics
        |
    Stage 3 (shortlisting) — 7-12 per region for newsroom blog
        |
    * Human Gate 1 -- topic approval (interrupt)
        |
    Stage 4 -- content generation:
        +-- 4A LinkedIn agent (top 5 topics x 3 voices)
        +-- 4B Blog writer agent (top 3 topics x 3 lenses)
        +-- 4D Newsroom blog (weekly: 7-12 items per region, 21-25 words)
              |
        +-- 4C Newsletter (bimonthly: curates from newsroom blog items)
        |
    Stage 5 (assemble review doc)
        |
    * Human Gate 2 -- content review (interrupt)
        |
    [revision loop if needed, max 2 rounds]
        |
    Stage 6 -- publish:
        +-- 6A LinkedIn publish
        +-- 6B Blog publish
        +-- 6C Newsletter publish
        |
    Stage 7 (performance feedback) -- delayed, runs 7 days later
"""

from langgraph.graph import END, StateGraph

from src.graph.state import PipelineState

# Import node functions
from src.graph.nodes.ingest import ingest_signals
from src.graph.nodes.topic_selection import select_topics
from src.graph.nodes.shortlisting import shortlist_topics
from src.graph.nodes.human_gate_1 import gate1_notify, gate1_wait
from src.graph.nodes.content_linkedin import generate_linkedin
from src.graph.nodes.content_blog import generate_blogs
from src.graph.nodes.content_newsroom import generate_newsroom_blog
from src.graph.nodes.content_newsletter import generate_newsletter
from src.graph.nodes.review_assembly import assemble_review_doc
from src.graph.nodes.human_gate_2 import gate2_notify, gate2_wait
from src.graph.nodes.revision import revise_drafts
from src.graph.nodes.publish import publish_linkedin, publish_blogs, publish_newsletter
from src.graph.nodes.feedback import collect_feedback
from src.settings import settings


def should_revise(state: PipelineState) -> str:
    """After Gate 2, decide whether to enter revision loop or proceed to publish."""
    if state.drafts_needing_revision and state.revision_round < 2:
        return "revise"
    return "publish"


def build_pipeline() -> StateGraph:
    """Construct the full pipeline graph."""

    graph = StateGraph(PipelineState)

    # -- Add nodes --
    # Stage 1
    graph.add_node("ingest", ingest_signals)

    # Stage 2
    graph.add_node("topic_selection", select_topics)

    # Stage 3
    graph.add_node("shortlisting", shortlist_topics)

    # Human Gate 1
    graph.add_node("gate1_notify", gate1_notify)
    graph.add_node("gate1_wait", gate1_wait)  # Uses interrupt()

    # Stage 4 -- content generation
    graph.add_node("linkedin_agent", generate_linkedin)      # 4A: top 5 topics x 3 voices
    graph.add_node("blog_agent", generate_blogs)              # 4B: top 3 topics x 3 lenses
    graph.add_node("newsroom_blog_agent", generate_newsroom_blog)  # 4D: weekly, 7-12 items/region
    graph.add_node("newsletter_agent", generate_newsletter)   # 4C: bimonthly, from newsroom items

    # Stage 5 -- review assembly
    graph.add_node("review_assembly", assemble_review_doc)

    # Human Gate 2
    graph.add_node("gate2_notify", gate2_notify)
    graph.add_node("gate2_wait", gate2_wait)  # Uses interrupt()

    # Revision loop
    graph.add_node("revise_drafts", revise_drafts)

    # Stage 6 -- publish
    graph.add_node("publish_linkedin", publish_linkedin)
    graph.add_node("publish_blogs", publish_blogs)
    graph.add_node("publish_newsletter", publish_newsletter)

    # Stage 7 -- feedback
    graph.add_node("feedback", collect_feedback)

    # -- Wire edges --

    # Sequential: Stage 1 -> 2 -> 3 -> Gate 1
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "topic_selection")
    graph.add_edge("topic_selection", "shortlisting")
    graph.add_edge("shortlisting", "gate1_notify")
    graph.add_edge("gate1_notify", "gate1_wait")

    # After Gate 1 approval -> fan out to content agents
    # Newsroom blog uses ranked_topics (7-12/region) — runs in parallel with LinkedIn & Blog
    # Newsletter runs AFTER newsroom blog because it curates from newsroom items
    graph.add_edge("gate1_wait", "linkedin_agent")      # uses shortlisted (top 5/region)
    graph.add_edge("gate1_wait", "blog_agent")           # uses shortlisted (top 3/region)
    graph.add_edge("gate1_wait", "newsroom_blog_agent")  # uses ranked (7-12/region)

    # Newsroom blog -> Newsletter (newsletter curates from newsroom items)
    graph.add_edge("newsroom_blog_agent", "newsletter_agent")

    # All content agents -> review assembly (fan-in: waits for all to complete)
    graph.add_edge("linkedin_agent", "review_assembly")
    graph.add_edge("blog_agent", "review_assembly")
    graph.add_edge("newsletter_agent", "review_assembly")

    # Review assembly -> Gate 2
    graph.add_edge("review_assembly", "gate2_notify")
    graph.add_edge("gate2_notify", "gate2_wait")

    # After Gate 2 -> conditional: revise or publish
    graph.add_conditional_edges(
        "gate2_wait",
        should_revise,
        {
            "revise": "revise_drafts",
            "publish": "publish_linkedin",
        },
    )

    # Revision loop -> back to gate2_notify for re-review
    graph.add_edge("revise_drafts", "gate2_notify")

    # Publish chain
    graph.add_edge("publish_linkedin", "publish_blogs")
    graph.add_edge("publish_blogs", "publish_newsletter")

    # All publish done -> feedback
    graph.add_edge("publish_newsletter", "feedback")

    # Feedback -> END
    graph.add_edge("feedback", END)

    return graph


def get_compiled_pipeline():
    """Compile the graph with Postgres checkpointing for persistence."""
    graph = build_pipeline()

    if settings.database_url.startswith("sqlite"):
        # Dev mode: no checkpointer (SQLite doesn't support PostgresSaver)
        return graph.compile()

    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        checkpointer = PostgresSaver.from_conn_string(settings.database_url)
        return graph.compile(checkpointer=checkpointer)
    except ImportError:
        return graph.compile()
