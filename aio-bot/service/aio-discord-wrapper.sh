#!/usr/bin/env bash
# Aio Discord Bot wrapper — runs claude --channels inside a named tmux session.
# Uses its own tmux server (-L aio) so it never shares global environment
# with Paimon's tmux server (-L paimon) or any other bot.
# Attach anytime: tmux -L aio attach -t aio
set -euo pipefail

SESSION="aio"
TMUX_SOCK="aio"
CLAUDE="$HOME/.local/bin/claude"
export DISCORD_STATE_DIR="/home/swegon/.claude/channels/aio-discord"

# --- Network gate ---------------------------------------------------------
echo "aio: waiting for Discord connectivity..."
net_end=$((SECONDS + 600))
until curl -sf --max-time 5 https://discord.com/api/v10/gateway >/dev/null 2>&1; do
    if [[ $SECONDS -ge $net_end ]]; then
        echo "aio: network unreachable after 600s — exit for systemd restart."
        exit 1
    fi
    sleep 5
done
echo "aio: Discord reachable — starting bot."

# Kill stale tmux session from old restarts and its bun server only —
# scoped to this session's process tree so Pom-Pom / Paimon aren't hit.
old_pid=$(tmux -L "$TMUX_SOCK" list-panes -t "$SESSION" -F '#{pane_pid}' 2>/dev/null | head -1 || true)
tmux -L "$TMUX_SOCK" kill-session -t "$SESSION" 2>/dev/null || true
if [[ -n "${old_pid:-}" ]]; then
    bun_pids=$(pstree -p "$old_pid" 2>/dev/null | grep -oP 'bun\(\K[0-9]+' || true)
    [[ -n "$bun_pids" ]] && kill -9 $bun_pids 2>/dev/null || true
fi
sleep 2

# Start claude --channels inside tmux, working dir = Aio_df (the
# product repo Aio works on, since the 2026-07-22 pivot). Persona lives at
# aio-bot/persona/aio-persona.md in this repo; global ~/.claude/CLAUDE.md
# just points here, gated on DISCORD_STATE_DIR, so it applies regardless of cwd.
tmux -L "$TMUX_SOCK" new-session -d -s "$SESSION" -c /home/swegon/AI_Agent/Aio_df \
    "DISCORD_STATE_DIR=$DISCORD_STATE_DIR $CLAUDE --model claude-sonnet-5 --permission-mode auto --dangerously-load-development-channels plugin:discord-aio@aio-marketplace"

# Auto-confirm workspace trust + MCP server trust dialogs (up to 60s).
sleep 2
end=$((SECONDS + 60))
while [[ $SECONDS -lt $end ]]; do
    tmux -L "$TMUX_SOCK" send-keys -t "$SESSION" "" Enter 2>/dev/null || true
    sleep 1.5
done

# Wait for bun discord server to appear in claude's process tree (up to 300s).
bun_wait_end=$((SECONDS + 300))
while [[ $SECONDS -lt $bun_wait_end ]]; do
    cpid=$(tmux -L "$TMUX_SOCK" list-panes -t "$SESSION" -F '#{pane_pid}' 2>/dev/null | head -1)
    if [[ -n "$cpid" ]] && pstree -p "$cpid" 2>/dev/null | grep -q "bun"; then
        echo "aio: bun server started (PID $cpid)"
        break
    fi
    sleep 5
done
cpid=$(tmux -L "$TMUX_SOCK" list-panes -t "$SESSION" -F '#{pane_pid}' 2>/dev/null | head -1)
if [[ -z "$cpid" ]] || ! pstree -p "$cpid" 2>/dev/null | grep -q "bun"; then
    echo "aio: ERROR — bun never started in claude process tree"
    tmux -L "$TMUX_SOCK" capture-pane -t "$SESSION" -p 2>/dev/null | head -20
    exit 1  # bun never started — systemd will restart service
fi

# Guardian — exits with code 1 if aio's bun dies (triggers systemd restart).
bun_guardian() {
    local had_bun=0
    while true; do
        sleep 30
        local cpid
        cpid=$(tmux -L "$TMUX_SOCK" list-panes -t "$SESSION" -F '#{pane_pid}' 2>/dev/null | head -1)
        [[ -z "$cpid" ]] && continue
        if pstree -p "$cpid" 2>/dev/null | grep -q "bun"; then
            had_bun=1
        elif [[ $had_bun -eq 1 ]]; then
            exit 1
        fi
    done
}
bun_guardian &

# Stay alive — systemd tracks this process; exit = service restart
while tmux -L "$TMUX_SOCK" has-session -t "$SESSION" 2>/dev/null; do
    sleep 5
done
