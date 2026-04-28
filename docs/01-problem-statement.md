# Problem Statement

## The Challenge

Amber's marketing team needs to produce high-quality, data-led content every two weeks across three channels (LinkedIn, Blog, Newsletter), targeting three distinct stakeholder audiences (Supply Partners, Universities/HE, HEA/Agents), across four regions (UK, USA, Australia, Europe).

Today this is done manually: someone reads industry sources, picks topics, writes drafts, gets them reviewed, and publishes. This process is:
- **Slow** — takes days per cycle
- **Inconsistent** — depends on who's doing it
- **Doesn't scale** — breaks as team grows or frequency increases

## The Goal

Build an automated content pipeline that:

1. **Monitors** relevant industry sources continuously
2. **Selects and ranks** topics using editorial rules
3. **Generates** channel-specific, audience-specific content drafts using AI
4. **Routes** all content through human review at the right moments
5. **Publishes** approved content to the right destinations
6. **Learns** from performance data to improve future cycles

## Traceability Requirement

The system must be fully traceable:
- Every piece of content linked back to the source signal that triggered it
- Every human decision logged
- Every AI output auditable

## Output Per Cycle

| Channel | Count | Details |
|---------|-------|---------|
| LinkedIn Posts | 15 | 5 topics x 3 voices (Amber Brand, Madhur, Jools) |
| Blog Posts | 3 | 1 per stakeholder audience (Supply, University, HEA) |
| Newsletter | 1 | 4 regional sections (UK, USA, Australia, Europe) |
| **Total** | **19** | Reviewed once, published to three channels |

## Human Control Points

Two human review gates per cycle:
1. **Topic Approval Gate** — after topic ranking, before content writing
2. **Content Review Gate** — after all drafts generated, before publishing

Everything between those gates is automated. Everything outside them is human-controlled.
