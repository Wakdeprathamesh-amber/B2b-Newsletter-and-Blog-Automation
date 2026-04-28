"""Stage 4A -- LinkedIn Content Generation.

Generates 5 topics x 3 voices = 15 LinkedIn post drafts.
Includes validation and one auto-revision attempt per draft.

In dev mode: returns sample LinkedIn posts.
"""

import json
from pathlib import Path

import structlog

from src.graph.state import PipelineState
from src.models.enums import DraftChannel, DraftStatus, DraftVoice, StakeholderAudience
from src.models.schemas import ContentDraft
from src.settings import settings

log = structlog.get_logger()

VOICE_CONFIGS = {
    DraftVoice.AMBER_BRAND: {
        "label": "Amber Homepage (B2B Brand)",
        "tone": "Crisp, signal-first, neutral but not passive. Real-time market signal layer. Answer: 'What just changed and why should you pay attention?' No opinions, no recommendations.",
        "format": "Bold declarative headline -> What happened (1-2 sentences) -> Key data (1-3 numbers) -> What it indicates (1-2 sentences) -> 5-8 hashtags",
        "length": "80-180 words",
        "hashtags": True,
        "rules": [
            "Start with a Unicode bold headline like a news wire: '𝗨𝗞 𝘃𝗶𝘀𝗮 𝗳𝗲𝗲 𝗿𝗲𝘃𝗶𝘀𝗶𝗼𝗻𝘀 𝗲𝗳𝗳𝗲𝗰𝘁𝗶𝘃𝗲 𝗔𝗽𝗿𝗶𝗹 𝟮𝟬𝟮𝟲'",
            "Keep it SHORT — max 3-4 tight blocks, no long narrative",
            "1-3 data points only — anchor credibility, not complexity",
            "Use directional cues: 'This highlights...', 'This reflects...', 'This indicates...'",
            "Never give opinions, analysis, or recommendations",
            "For negative news: present facts neutrally, no negative sector impact commentary",
            "Bold key figures and phrases",
            "Max 1 emoji (🌏 🗞️ 📃) placed near headline",
            "5-8 hashtags: #amber #amberstudent #PBSA #InternationalEducation #StudentMobility #AmberInsights",
            "NEVER use 'I' — this is a brand account",
        ],
    },
    DraftVoice.MADHUR: {
        "label": "Madhur Gujar — Co-Founder & CBO",
        "tone": "Authoritative, precise, data-forward. Intelligence briefing made public. Measured and unsensational. Advisor-first, promoter-second. Intellectually honest — comfortable saying 'too early to tell'.",
        "format": "Unicode bold headline (report heading) -> Data layer with ▼ ▲ arrows & YoY -> Interpretation -> 'Amber's View →' italicised callout -> Sign-off -> 5-8 hashtags",
        "length": "200-400 words",
        "hashtags": True,
        "rules": [
            "Start with Unicode bold headline: '𝗨𝗞 𝗦𝘁𝘂𝗱𝘆 𝗩𝗶𝘀𝗮 𝗖𝗹𝗲𝗮𝗿𝗮𝗻𝗰𝗲: 𝗠𝗮𝗿𝗰𝗵 𝟮𝟬𝟮𝟲 𝗨𝗽𝗱𝗮𝘁𝗲'",
            "Data is CENTRAL — multiple specific figures, YoY comparisons, direction indicators (▼ ▲ →)",
            "Use bold for headers, labels, key figures",
            "Use bullet points (•) for data items",
            "Include '𝘈𝘮𝘣𝘦𝘳'𝘴 𝘷𝘪𝘦𝘸 →' or '𝘈𝘮𝘣𝘦𝘳'𝘴 𝘛𝘢𝘬𝘦 →' — italicised callout with strategic recommendation",
            "Add nuance: 'Visa clearances ≠ demand automatically'",
            "Mix personal POV ('I') with institutional framing ('Amber's view')",
            "Sign off: 'Stay tuned for more insights' / 'Watch this space'",
            "5-8 hashtags at end",
            "Every sentence must be load-bearing — no padding",
            "Cite sources inline (Enroly, UCAS, Home Office, BONARD)",
            "No vague claims, no alarm without context, no drama",
        ],
    },
    DraftVoice.JOOLS: {
        "label": "Jools Horton-Lakins — Director of University Partnerships",
        "tone": "Collegiate, peer-oriented HE insider. Thoughtful and considered. Curious, open-ended — poses questions rather than conclusions. Purpose-driven — connects to student welfare. Warm but professional.",
        "format": "Audience signal ('Resharing for colleagues in Accommodation 🏠, Finance 💰, Recruitment 👩‍🎓') -> External view value -> Stakeholder-segmented implications -> Open invitation -> Reflective question -> Heavy hashtags",
        "length": "200-350 words",
        "hashtags": True,
        "rules": [
            "Open with explicit audience signal: 'Resharing this for colleagues across Higher Education'",
            "Position data as offering the external market-wide view beyond one institution's pipeline",
            "Break down implications by university function: Accommodation → occupancy; Finance → variance; Recruitment → pipeline vs conversion",
            "Close with generous offer: 'I'm happy to share more granular cuts — by city, segment, or source market'",
            "Use rhetorical questions as a signature habit",
            "Moderate emoji: 🏠💰👩‍🎓 for stakeholder groups, 🤔 for reflection, 🌍 for global scope",
            "Heavy global hashtags: #HigherEducation #UniversityPartnerships #InternationalStudents #IntlEd #HigherEdUK #StudentAccommodation plus destination-specific tags",
            "Write FOR university sector, NOT for PBSA operators",
            "No hard commercial pitch — Amber is a knowledge partner, not a booking platform",
            "Never neglect the student welfare dimension",
            "Comfortable with nuance — longer, discursive, essay-like",
        ],
    },
}


async def generate_linkedin(state: PipelineState) -> dict:
    """Generate LinkedIn post drafts from top 5 topics x 3 voices = 15 posts.

    Uses the top 5 shortlisted topics (by rank) even though the full
    shortlist may contain 35-55 topics for the newsroom blog.
    """

    cycle = state.cycle
    # LinkedIn uses top 5 topics only (not the full newsroom blog shortlist)
    topics = sorted(state.shortlisted_topics, key=lambda t: t.rank)[:5]
    errors: list[str] = []

    log.info("stage4a_start", cycle_id=cycle.cycle_id, topic_count=len(topics))

    # -- Dev mode: return sample posts --
    if settings.dev_mode or not settings.is_llm_available:
        from src.sample_data import get_sample_linkedin_draft
        drafts = []
        voices = [DraftVoice.AMBER_BRAND, DraftVoice.MADHUR, DraftVoice.JOOLS]
        for topic in topics:
            for voice in voices:
                draft = get_sample_linkedin_draft(topic, voice, cycle.cycle_id)
                draft.validation_flags = _validate_linkedin_post(
                    draft.content_body, voice, draft.word_count
                )
                drafts.append(draft)
        log.info("stage4a_complete_dev_mode", draft_count=len(drafts))
        return {"linkedin_drafts": drafts, "errors": errors}

    # -- Production mode --
    drafts: list[ContentDraft] = []
    prompt_template = Path("prompts/linkedin-post.md").read_text()

    from src.llm import complete

    voices = [DraftVoice.AMBER_BRAND, DraftVoice.MADHUR, DraftVoice.JOOLS]

    for topic in topics:
        for voice in voices:
            voice_config = VOICE_CONFIGS[voice]

            generation_prompt = f"""{prompt_template}

## This Specific Post

Topic: {topic.edited_title or topic.title}
Summary: {topic.edited_summary or topic.summary}
Content guidance: {topic.content_guidance}
Region: {topic.primary_region}
Stakeholder audience: {', '.join(topic.stakeholder_tags)}

## Voice for This Post
Voice: {voice_config['label']}
Tone: {voice_config['tone']}
Format: {voice_config['format']}
Length: {voice_config['length']}
Include hashtags: {voice_config['hashtags']}
Rules: {json.dumps(voice_config['rules'])}

Write the LinkedIn post now. Return ONLY the post text (and hashtags if applicable)."""

            try:
                content_body = await complete(
                    role="generation",
                    messages=[{"role": "user", "content": generation_prompt}],
                    max_tokens=1500,
                )
                word_count = len(content_body.split())
                flags = _validate_linkedin_post(content_body, voice, word_count)

                draft = ContentDraft(
                    cycle_id=cycle.cycle_id,
                    topic_id=topic.topic_id,
                    channel=DraftChannel.LINKEDIN,
                    audience=_primary_audience(topic.stakeholder_tags),
                    voice=voice,
                    content_body=content_body,
                    word_count=word_count,
                    generation_prompt=generation_prompt,
                    generation_model=settings.generation_model,
                    status=DraftStatus.DRAFT,
                    validation_flags=flags,
                )

                if flags:
                    revised = await _auto_revise(draft, flags)
                    if revised:
                        draft = revised

                drafts.append(draft)

            except Exception as e:
                errors.append(f"LinkedIn generation failed: {topic.title} / {voice} -- {e}")
                log.error("linkedin_gen_failed", topic=topic.title, voice=voice, error=str(e))
                drafts.append(ContentDraft(
                    cycle_id=cycle.cycle_id,
                    topic_id=topic.topic_id,
                    channel=DraftChannel.LINKEDIN,
                    voice=voice,
                    content_body="[Generation failed -- see error log]",
                    generation_prompt=generation_prompt,
                    status=DraftStatus.GENERATION_FAILED,
                ))

    log.info("stage4a_complete", draft_count=len(drafts))
    return {"linkedin_drafts": drafts, "errors": errors}


def _validate_linkedin_post(content: str, voice: DraftVoice, word_count: int) -> list[str]:
    """Validate a LinkedIn post against voice-specific rules."""
    flags = []

    # Word count ranges per voice
    if voice == DraftVoice.AMBER_BRAND:
        if word_count < 60 or word_count > 200:
            flags.append(f"word_count_out_of_range ({word_count}, target: 80-180)")
    elif voice == DraftVoice.MADHUR:
        if word_count < 150 or word_count > 450:
            flags.append(f"word_count_out_of_range ({word_count}, target: 200-400)")
    elif voice == DraftVoice.JOOLS:
        if word_count < 150 or word_count > 400:
            flags.append(f"word_count_out_of_range ({word_count}, target: 200-350)")

    # Amber Brand should never use "I"
    if voice == DraftVoice.AMBER_BRAND and " I " in content:
        flags.append("amber_brand_used_I")

    # Madhur must have hashtags and "Amber's view/take"
    if voice == DraftVoice.MADHUR:
        if "#" not in content:
            flags.append("madhur_missing_hashtags")
        content_lower = content.lower()
        if "amber's view" not in content_lower and "amber's take" not in content_lower:
            flags.append("madhur_missing_ambers_view_callout")

    # Jools now DOES use hashtags (heavy global sweep)
    if voice == DraftVoice.JOOLS and "#" not in content:
        flags.append("jools_missing_hashtags")

    if len(content) > 3000:
        flags.append("exceeds_linkedin_character_limit")

    return flags


async def _auto_revise(draft: ContentDraft, flags: list[str]) -> ContentDraft | None:
    """Attempt one automatic revision to fix validation flags."""
    from src.llm import complete

    try:
        revision_prompt = f"""The following LinkedIn post has validation issues that need fixing.

CURRENT POST:
{draft.content_body}

ISSUES TO FIX:
{json.dumps(flags)}

Rewrite the post fixing ONLY the flagged issues. Keep the same topic, data points, and tone.
Return ONLY the revised post text."""

        revised_body = await complete(
            role="generation",
            messages=[{"role": "user", "content": revision_prompt}],
            max_tokens=1500,
        )
        revised_word_count = len(revised_body.split())
        new_flags = _validate_linkedin_post(revised_body, draft.voice, revised_word_count)

        if len(new_flags) < len(flags):
            draft.content_body = revised_body
            draft.word_count = revised_word_count
            draft.validation_flags = new_flags
            draft.revision_count = 1
            return draft

    except Exception:
        pass

    return None


def _primary_audience(tags: list[str]) -> StakeholderAudience | None:
    """Get the primary audience from stakeholder tags."""
    if not tags:
        return None
    mapping = {
        "Supply": StakeholderAudience.SUPPLY,
        "University": StakeholderAudience.UNIVERSITY,
        "HEA": StakeholderAudience.HEA,
    }
    return mapping.get(tags[0])
