#!/bin/bash
# Cloud sessions only: install project deps, Graphify (code knowledge graph) and claude-mem (local session memory).
# Idempotent and non-interactive. Memory/graph tooling is best-effort: a failure there never blocks the session.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
export PATH="$HOME/.local/bin:$PATH"
[ -n "${CLAUDE_ENV_FILE:-}" ] && echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$CLAUDE_ENV_FILE"

pip install -q -r requirements.txt

# Graphify: the graphify command must exist because .claude/settings.json hooks call it.
command -v graphify >/dev/null || uv tool install graphifyy
graphify update . >/dev/null 2>&1 || echo "graphify: graph build skipped (non-fatal)"

# claude-mem, local only: no account, no hosted memory, telemetry off. Memory lives in ~/.claude-mem in this container.
if [ ! -d "$HOME/.claude/plugins/cache/thedotmack/claude-mem" ]; then
  CI=true CLAUDE_MEM_ONLINE_OPTIN=false npx --yes claude-mem install --ide claude-code --provider claude >/dev/null 2>&1 \
    || echo "claude-mem: install failed (non-fatal)"
fi
npx --yes claude-mem telemetry disable >/dev/null 2>&1 || true
npx --yes claude-mem start >/dev/null 2>&1 || echo "claude-mem: worker not started (non-fatal)"
