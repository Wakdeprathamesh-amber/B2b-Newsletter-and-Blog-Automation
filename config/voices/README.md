# Voice & Brand Reference

This folder contains the source-of-truth documentation for all content voices used by the Amber Content Engine.

## Files

| File | Voice | Used By |
|---|---|---|
| `madhur-gujar.md` | Madhur Gujar (CBO) — data-led market intelligence briefings | LinkedIn generation (Madhur voice) |
| `jools-horton-lakins.md` | Jools Horton-Lakins (Dir. University Partnerships) — university sector peer voice | LinkedIn generation (Jools voice) |
| `amber-homepage.md` | Amber Brand — real-time market signal feed | LinkedIn generation (Amber Brand voice) |

## How These Are Used

The generation prompt at `prompts/linkedin-post.md` contains a condensed version of each voice profile. When updating voices:

1. Update the full doc here first (source of truth)
2. Update `prompts/linkedin-post.md` to match
3. Update `src/graph/nodes/content_linkedin.py` VOICE_CONFIGS to match

## Adding New Voices

Create a new `.md` file following the same structure:
- Who They Are (persona)
- Tone
- Voice & Style
- Post Structure
- Example Posts (real)
- What NOT to Do
