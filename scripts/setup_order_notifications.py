#!/usr/bin/env python3
"""Set up and test Telegram order notifications.

The shop pushes every new order to Telegram (src/lib/store/notify.ts). That
needs two values in the environment:

    TELEGRAM_BOT_TOKEN   from @BotFather when you create the bot
    TELEGRAM_CHAT_ID     the chat the bot should message -- usually you

Getting the chat ID is the awkward part, because Telegram will not tell a bot
who you are until you have spoken to it first. This script does the whole loop:

    1. `--whoami`  checks the token and prints the bot's @username.
    2. `--chats`   lists every chat that has messaged the bot, with its ID.
                   Send your bot any message first, then run this.
    3. `--test`    sends a realistic sample order to TELEGRAM_CHAT_ID, so you
                   can see exactly what a real order will look like.

Read locally from .env.local; set the same two variables in Vercel for
production. Nothing here writes to the database.

Usage:
    python -X utf8 scripts/setup_order_notifications.py --whoami
    python -X utf8 scripts/setup_order_notifications.py --chats
    python -X utf8 scripts/setup_order_notifications.py --test
"""
import argparse
import io
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
API = "https://api.telegram.org"

SAMPLE = """🛒 <b>New order GM-1042</b>

• 2 × Mathematics B — Chapterwise Workbook, Part 1 — ৳1,200

Subtotal ৳1,200 + delivery ৳70
<b>Total ৳1,270</b> — Cash on delivery

<b>Rafiq Hasan</b>
📞 01712345678
✉️ rafiq@example.com

House 12, Road 5, Dhanmondi, Dhaka
Dhaka

<i>(sample — sent by setup_order_notifications.py)</i>"""


def require_token() -> bool:
    if TOKEN:
        return True
    print("TELEGRAM_BOT_TOKEN is not set.\n")
    print("  1. Open Telegram and message @BotFather")
    print("  2. Send /newbot and follow the prompts")
    print("  3. Put the token it gives you in .env.local as TELEGRAM_BOT_TOKEN")
    print("     (and in the Vercel project settings for production)")
    return False


def cmd_whoami() -> None:
    if not require_token():
        return
    r = httpx.get(f"{API}/bot{TOKEN}/getMe", timeout=30)
    data = r.json()
    if not data.get("ok"):
        print(f"Telegram rejected the token: {data.get('description')}")
        return
    bot = data["result"]
    print(f"token OK — bot is @{bot.get('username')} ({bot.get('first_name')})")
    print(f"chat id currently configured: {CHAT_ID or '(none)'}")


def cmd_chats() -> None:
    if not require_token():
        return
    r = httpx.get(f"{API}/bot{TOKEN}/getUpdates", timeout=30)
    data = r.json()
    if not data.get("ok"):
        print(f"Telegram rejected the request: {data.get('description')}")
        return
    seen: dict[str, str] = {}
    for update in data.get("result", []):
        msg = update.get("message") or update.get("channel_post") or {}
        chat = msg.get("chat") or {}
        if chat.get("id") is not None:
            who = chat.get("username") or chat.get("title") or chat.get("first_name") or "?"
            seen[str(chat["id"])] = f"{who} ({chat.get('type')})"
    if not seen:
        print("No chats yet. Open Telegram, send your bot any message, then re-run this.")
        print("(Telegram only reveals a chat to a bot after that chat has written to it.)")
        return
    print("Chats that have messaged the bot:\n")
    for chat_id, who in seen.items():
        print(f"  TELEGRAM_CHAT_ID={chat_id}    {who}")


def cmd_test() -> None:
    if not require_token():
        return
    if not CHAT_ID:
        print("TELEGRAM_CHAT_ID is not set — run with --chats to find it.")
        return
    r = httpx.post(f"{API}/bot{TOKEN}/sendMessage", timeout=30, json={
        "chat_id": CHAT_ID,
        "text": SAMPLE,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })
    data = r.json()
    if data.get("ok"):
        print("Sent. Check your phone — a real order will look exactly like that.")
    else:
        print(f"Telegram refused it: {data.get('description')}")
        if "chat not found" in str(data.get("description", "")).lower():
            print("The chat ID looks wrong. Run with --chats to list the right one.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--whoami", action="store_true", help="check the token, name the bot")
    ap.add_argument("--chats", action="store_true", help="list chat IDs that have messaged the bot")
    ap.add_argument("--test", action="store_true", help="send a sample order notification")
    args = ap.parse_args()

    if args.whoami:
        cmd_whoami()
    elif args.chats:
        cmd_chats()
    elif args.test:
        cmd_test()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
