# Core Data Entities

## Signal (Stage 1 Output)

A raw piece of information captured from a monitored source.

| Field | Type | Description |
|-------|------|-------------|
| signal_id | string | Unique identifier |
| source_name | string | e.g. "HESA", "Knight Frank" |
| source_url | string | URL of original article/report |
| headline | string | Title of the content |
| summary | string | 1-3 sentence description |
| published_date | datetime | When the source published it |
| region | enum | UK / USA / Australia / Europe / Global |
| topic_category | enum | Rent Trends / Visa Data / Student Demand / Policy Changes / Supply Outlook / Emerging Markets / QS Rankings / Other |
| raw_content | string | Full extracted text |
| is_negative_news | bool | Flagged during tagging |
| mentions_competitor | bool | Flagged during tagging |
| is_politically_sensitive | bool | Flagged during tagging |
| tagging_failed | bool | True if AI couldn't confidently tag |
| captured_at | datetime | When system captured this |
| cycle_id | string | Which cycle this belongs to |

## Topic (Stages 2-3 Output)

A ranked editorial topic derived from one or more signals.

| Field | Type | Description |
|-------|------|-------------|
| topic_id | string | Unique identifier |
| cycle_id | string | Which cycle |
| title | string | Max 80 chars |
| summary | string | 2-3 sentences: what and why it matters |
| rank | int | 1-15 (1 = highest priority) |
| urgency | enum | Breaking / Time-sensitive / Evergreen |
| primary_region | enum | Main region |
| secondary_regions | list | Other relevant regions |
| stakeholder_tags | list | Supply / University / HEA |
| source_signal_ids | list | Signal IDs supporting this topic |
| rationale | string | Why AI ranked it here |
| content_guidance | string | 1-2 sentences of editorial direction |
| urgency_score | float | 1-10 |
| regional_relevance_score | float | 1-10 |
| stakeholder_fit_score | float | 1-10 |
| total_score | float | Weighted composite |
| status | enum | Pending / Approved / Edited / Rejected |
| approved_by | string | Reviewer name |
| approved_at | datetime | When approved |
| edited_title | string | If human changed it |
| edited_summary | string | If human changed it |
| performance_score | float | From Stage 7 feedback |

## ContentDraft (Stage 4 Output)

A single piece of generated content.

| Field | Type | Description |
|-------|------|-------------|
| draft_id | string | Unique identifier |
| cycle_id | string | Which cycle |
| topic_id | string | Which topic |
| channel | enum | LinkedIn / Blog / Newsletter |
| audience | enum | Supply / University / HEA / All |
| voice | enum | AmberBrand / Madhur / Jools / BlogSupply / BlogUniversity / BlogHEA / NewsletterGlobal |
| content_body | string | Full generated text |
| word_count | int | Length |
| generation_prompt | string | Exact prompt sent to AI |
| generation_model | string | Which model |
| generated_at | datetime | When generated |
| status | enum | Draft / UnderReview / RevisionRequested / Approved / Published / Blocked / GenerationFailed |
| review_comments | string | Human feedback |
| revised_body | string | After revision |
| revised_at | datetime | When revised |
| revision_count | int | How many revision rounds |
| validation_flags | list | Issues found during validation |
| published_at | datetime | When published |
| published_url | string | URL of published content |

## Cycle

A single run of the full pipeline.

| Field | Type | Description |
|-------|------|-------------|
| cycle_id | string | e.g. "2025-W15" |
| started_at | datetime | When started |
| stage | int | Current stage (1-7) |
| status | enum | Running / AwaitingTopicApproval / AwaitingContentReview / Publishing / Complete / Failed / Cancelled |
| topics_approved_at | datetime | Gate 1 completion |
| content_approved_at | datetime | Gate 2 completion |
| completed_at | datetime | When finished |
| error_log | list | Any errors |
| signal_count | int | Signals captured |
| topic_count | int | Topics shortlisted |
| draft_count | int | Drafts generated |

## ReviewSession

A logged record of a human review event.

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Unique identifier |
| cycle_id | string | Which cycle |
| gate | enum | TopicApproval / ContentReview |
| reviewer_name | string | Who reviewed |
| started_at | datetime | When opened |
| completed_at | datetime | When submitted |
| decisions | list | Array of {item_id, action, comment} |

## LogEntry

Audit trail for every system action.

| Field | Type | Description |
|-------|------|-------------|
| log_id | string | Unique identifier |
| cycle_id | string | Which cycle |
| stage | int | Which stage |
| event_type | string | signal_captured / topic_ranked / draft_generated / human_approved / published / error |
| entity_type | string | Signal / Topic / ContentDraft / Cycle / ReviewSession |
| entity_id | string | Affected entity |
| actor | string | "system" or human name |
| timestamp | datetime | When it happened |
| details | JSON | Event-specific context |
