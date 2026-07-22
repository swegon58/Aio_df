# aio-bot/CLAUDE.md

This folder is the **portable source of truth** for how Claude Code operates as
"Aio" over Discord on this project. Before this folder existed, every piece
below lived scattered under the local machine's `~/.claude/` home directory,
untracked by git — a fresh clone on another machine would boot with no
persona, no bot, and no memory. Everything needed to reproduce that is here
now; only per-machine secrets (bot token, allowlist) stay outside git.

See [SETUP.md](SETUP.md) for bring-up steps on a new machine.

## Layout

```
aio-bot/
├── persona/aio-persona.md         # Discord persona rules (speech, tone, reply protocol)
├── discord-plugin/                # Local Claude Code plugin marketplace + the plugin itself
│   ├── .claude-plugin/marketplace.json
│   └── discord-plugin/            # MCP server (reply/edit_message/react/fetch_messages/...)
│       ├── server.ts              # bun + discord.js MCP server, driven by DISCORD_STATE_DIR
│       └── skills/{access,configure}/SKILL.md
├── service/                       # systemd --user units + the scripts they run
│   ├── aio-discord.service        # runs `claude --channels plugin:discord-aio@aio-marketplace`
│   ├── aio-discord-wrapper.sh     # tmux-wrapped launcher, network gate, bun-death guardian
│   ├── aio-cmd-watcher.service    # watches Discord for !clear / !compact
│   └── aio-discord-command-watcher.py
└── memory/                        # durable, git-tracked continuity notes (see below)
```

## How it boots

1. systemd (`aio-discord.service`) runs `aio-discord-wrapper.sh`, which starts
   `claude --channels plugin:discord-aio@aio-marketplace` inside a dedicated
   tmux session (`tmux -L aio`), with `DISCORD_STATE_DIR` pointing at the
   machine-local channel state dir (bot token, allowlist, per-channel session
   files — never in git).
2. The persona activates because the user's **global** `~/.claude/CLAUDE.md`
   has a one-line gate: when `DISCORD_STATE_DIR` matches the Aio channel, follow
   `aio-bot/persona/aio-persona.md` in *this* repo. That global pointer is the
   only piece that can't live in git (Claude Code reads it before it knows any
   repo exists) — everything it points to does.
3. `discord-aio@aio-marketplace` resolves through `extraKnownMarketplaces` in
   the user's global `settings.json`, which points at
   `aio-bot/discord-plugin/` in this repo (a plain path — swap machines by
   repointing this one string, see SETUP.md).
4. `aio-cmd-watcher.service` runs alongside it, polling Discord for `!compact`
   / `!clear` and driving the same tmux session via `send-keys`.

## Memory model

Two layers exist, deliberately:

- **Local auto-memory** (`~/.claude/projects/<hash>/memory/`) — Claude Code's
  built-in per-project memory. Fast, automatic, but keyed by the repo's
  absolute path hash, so it does **not** survive a clone to a new machine or
  path.
- **`aio-bot/memory/`** (this folder) — the portable copy. `MEMORY.md` is the
  index; each topic gets its own file. This is what makes continuity survive
  `git pull` on another machine. When you write a durable memory worth keeping
  across machines, mirror it here (not just in the local auto-memory).

## What deliberately stays out of git

- `~/.claude/channels/aio-discord/.env` — Discord bot token.
- `~/.claude/channels/aio-discord/access.json` — allowlist (per-machine pairing state).
- `~/.claude/channels/aio-discord/inbox/`, `channel-sessions/` — runtime state/attachments.

Rebuild these on a new machine via the plugin's own `/discord:configure` and
`/discord:access` skills — see SETUP.md.
