# Bringing Aio's Discord bot up on a new machine

Everything code/config-shaped is in this folder and travels with `git clone` /
`git pull`. Only secrets and this-machine state need to be created fresh.

## 1. Register the plugin marketplace

In the user's global `~/.claude/settings.json`, add (or repoint) an entry
under `extraKnownMarketplaces`:

```json
"aio-marketplace": {
  "source": { "path": "/absolute/path/to/Aio_df/aio-bot/discord-plugin", "source": "directory" }
}
```

And enable the plugin under `enabledPlugins`: `"discord-aio@aio-marketplace": true`.

Install its deps once:

```bash
cd Aio_df/aio-bot/discord-plugin/discord-plugin && bun install
```

## 2. Wire the persona pointer

In the user's global `~/.claude/CLAUDE.md`, add:

```
## Persona: Aio (Discord)
When `DISCORD_STATE_DIR=<path-to-channel-state-dir>` (Aio bot service session), follow
`/absolute/path/to/Aio_df/aio-bot/persona/aio-persona.md`. Only applies to that Discord
session, not normal CLI work.
```

Pick a channel state dir, e.g. `~/.claude/channels/aio-discord` (created by step 3).

## 3. Configure the Discord bot (secrets — never in git)

Run the plugin's own setup skill: `/discord:configure`. It asks for the bot
token and writes `<channel-state-dir>/.env`. Then `/discord:access` to set who
can reach it (writes `<channel-state-dir>/access.json`).

## 4. Install the systemd services

Copy the two unit files, edit paths if the repo lives somewhere other than
`/home/swegon/AI_Agent/Aio_df`, then link + enable:

```bash
cp aio-bot/service/aio-discord.service aio-bot/service/aio-cmd-watcher.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now aio-discord.service aio-cmd-watcher.service
```

`aio-discord-wrapper.sh` and `aio-discord-command-watcher.py` are run in place
from `aio-bot/service/` (the unit files' `ExecStart` points there directly) —
no separate copy needed for those two.

## 5. Memory continuity

`aio-bot/memory/MEMORY.md` + its topic files carry over automatically with
git. Claude Code's own local auto-memory (`~/.claude/projects/.../memory/`)
starts empty on a new machine/path — that's expected; it's a local cache, not
the source of truth. Point a fresh session at `aio-bot/memory/MEMORY.md` if it
needs the backstory.
