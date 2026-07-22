#!/usr/bin/env python3
"""
Discord command watcher for Aio.
Polls for !clear and !compact from the authorized user.
  !compact -> tmux send-keys /compact (context compression, keeps summary)
  !clear   -> tmux send-keys /clear   (full context wipe, session stays up)
"""
import os
import time
import json
import subprocess
import urllib.request
import urllib.parse
import urllib.error

CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID", "1519020450322317362")
AUTHORIZED_USER = "795796577524252712"
POLL_INTERVAL = 4  # seconds
TMUX_SESSION = "aio"

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
if not TOKEN:
    env_path = os.path.expanduser("/home/swegon/.claude/channels/aio-discord/.env")
    with open(env_path) as f:
        for line in f:
            if line.startswith("DISCORD_BOT_TOKEN="):
                TOKEN = line.strip().split("=", 1)[1]
                break

HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "DiscordBot (aio-cmd-watcher, 1.0)",
}

BASE = "https://discord.com/api/v10"


def api_get(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"Request error: {e}")
        return []


def api_put(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS, method="PUT")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def react(message_id, emoji="✅"):
    encoded = urllib.parse.quote(emoji)
    api_put(f"/channels/{CHANNEL_ID}/messages/{message_id}/reactions/{encoded}/@me")


def do_compact():
    subprocess.run(
        ["tmux", "-L", TMUX_SESSION, "send-keys", "-t", TMUX_SESSION, "/compact", "Enter"],
        check=False,
    )
    print("Sent /compact to tmux session")


def do_clear():
    subprocess.run(
        ["tmux", "-L", TMUX_SESSION, "send-keys", "-t", TMUX_SESSION, "/clear", "Enter"],
        check=False,
    )
    print("Sent /clear to tmux session")


def get_messages(after=None):
    path = f"/channels/{CHANNEL_ID}/messages?limit=10"
    if after:
        path += f"&after={after}"
    return api_get(path)


def main():
    msgs = get_messages()
    last_id = msgs[0]["id"] if msgs else None
    print(f"Aio command watcher started. Channel: {CHANNEL_ID}. Last ID: {last_id}")

    while True:
        time.sleep(POLL_INTERVAL)
        new_msgs = get_messages(after=last_id)
        if not new_msgs:
            continue

        # Discord returns newest-first; process oldest-first to keep order.
        for msg in reversed(new_msgs):
            last_id = msg["id"]
            author = msg.get("author", {})
            if author.get("id") != AUTHORIZED_USER:
                continue
            content = msg.get("content", "").strip().lower()
            if content == "!compact":
                do_compact()
                react(msg["id"], "🧠")
            elif content == "!clear":
                do_clear()
                react(msg["id"], "🧹")


if __name__ == "__main__":
    main()
