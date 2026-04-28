"""Connectivity diagnostic for Phase 1 V1.

Verifies:
1. .env loads correctly
2. OpenAI API key works (sends a 1-token ping)
3. Google service account JSON exists and parses
4. Google Sheet is accessible (read + write test)

Run:  python3 check_setup.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path


# ── Minimal .env loader (no external deps) ────────────────────────────────
def load_env(path: str = ".env") -> dict:
    env = {}
    if not Path(path).exists():
        return env
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def ok(msg: str) -> None:
    print(f"  \033[32m[OK]\033[0m   {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31m[FAIL]\033[0m {msg}")


def warn(msg: str) -> None:
    print(f"  \033[33m[WARN]\033[0m {msg}")


def section(title: str) -> None:
    print(f"\n── {title} " + "─" * (60 - len(title)))


# ── Checks ────────────────────────────────────────────────────────────────
async def check_openai(api_key: str) -> bool:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        fail("openai package not installed — run: pip install openai")
        return False

    if not api_key or api_key.startswith("sk-proj-YOUR") or api_key == "":
        fail("OPENAI_API_KEY is missing or still a placeholder")
        return False

    client = AsyncOpenAI(api_key=api_key)
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Reply with the single word: pong"}],
            max_tokens=5,
        )
        reply = resp.choices[0].message.content.strip()
        ok(f"OpenAI reachable — model replied: {reply!r}")
        return True
    except Exception as e:
        fail(f"OpenAI request failed: {e}")
        return False


def check_google_json(path: str) -> dict | None:
    if not path or "path/to" in path:
        fail("GOOGLE_SERVICE_ACCOUNT_JSON is missing or still a placeholder")
        return None

    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        fail(f"Credentials file not found at: {file_path}")
        return None

    try:
        data = json.loads(file_path.read_text())
    except Exception as e:
        fail(f"Credentials file is not valid JSON: {e}")
        return None

    required = {"type", "project_id", "private_key", "client_email"}
    missing = required - set(data.keys())
    if missing:
        fail(f"Credentials JSON missing fields: {missing}")
        return None

    if data["type"] != "service_account":
        fail(f"Credentials type is {data['type']!r}, expected 'service_account'")
        return None

    ok(f"Credentials JSON valid — client_email: {data['client_email']}")
    return data


def check_google_sheet(cred_path: str, sheet_id: str, cred_data: dict) -> bool:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        fail("gspread or google-auth not installed")
        return False

    if not sheet_id or "your-sheet-id" in sheet_id:
        fail("GOOGLE_MASTER_SHEET_ID is missing or still a placeholder")
        return False

    file_path = Path(cred_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    try:
        creds = Credentials.from_service_account_file(str(file_path), scopes=scopes)
        client = gspread.authorize(creds)
    except Exception as e:
        fail(f"Failed to authenticate with Google: {e}")
        return False

    try:
        sheet = client.open_by_key(sheet_id)
        ok(f"Sheet opened: {sheet.title!r}")
    except gspread.exceptions.APIError as e:
        msg = str(e)
        if "PERMISSION_DENIED" in msg or "403" in msg:
            fail(
                "Permission denied. Share the sheet with:\n"
                f"         {cred_data['client_email']}\n"
                "         (Editor access)"
            )
        elif "NOT_FOUND" in msg or "404" in msg:
            fail(f"Sheet ID not found: {sheet_id}")
        else:
            fail(f"Sheet API error: {e}")
        return False
    except Exception as e:
        fail(f"Unexpected error opening sheet: {e}")
        return False

    try:
        worksheets = sheet.worksheets()
        ok(f"Found {len(worksheets)} worksheet(s): {[w.title for w in worksheets]}")
    except Exception as e:
        warn(f"Could not list worksheets: {e}")

    try:
        test_ws = sheet.sheet1
        test_ws.update("Z1", [["ping"]])
        val = test_ws.acell("Z1").value
        test_ws.update("Z1", [[""]])
        if val == "ping":
            ok("Write + read test passed (cell Z1)")
        else:
            warn(f"Wrote 'ping' but read back {val!r}")
    except gspread.exceptions.APIError as e:
        msg = str(e)
        if "PERMISSION_DENIED" in msg or "403" in msg:
            fail("Can read but cannot write — give the service account Editor (not Viewer) access")
            return False
        fail(f"Write test failed: {e}")
        return False

    return True


# ── Main ──────────────────────────────────────────────────────────────────
async def main() -> int:
    print("\n" + "═" * 68)
    print("  Amber Content Engine — Phase 1 V1 setup check")
    print("═" * 68)

    env = load_env()
    if not env:
        fail(".env file not found or empty")
        return 1

    section("Environment")
    keys_present = sorted(env.keys())
    print(f"  Loaded {len(keys_present)} keys from .env: {keys_present}")

    section("OpenAI")
    openai_ok = await check_openai(env.get("OPENAI_API_KEY", ""))

    section("Google — service account JSON")
    cred_data = check_google_json(env.get("GOOGLE_SERVICE_ACCOUNT_JSON", ""))

    sheet_ok = False
    if cred_data:
        section("Google — Sheet access")
        sheet_ok = check_google_sheet(
            env.get("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
            env.get("GOOGLE_MASTER_SHEET_ID", ""),
            cred_data,
        )

    section("Firecrawl")
    fc_key = env.get("FIRECRAWL_API_KEY", "")
    if fc_key and not fc_key.startswith("fc-..."):
        ok(f"FIRECRAWL_API_KEY present ({fc_key[:8]}...)")
    else:
        warn("FIRECRAWL_API_KEY missing — scraping stage will not work")

    print("\n" + "═" * 68)
    all_ok = openai_ok and cred_data is not None and sheet_ok
    if all_ok:
        print("  \033[32mAll checks passed. You're ready for Phase 1 V1.\033[0m")
    else:
        print("  \033[31mSome checks failed — see messages above.\033[0m")
    print("═" * 68 + "\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
