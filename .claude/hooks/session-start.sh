#!/bin/bash
# SessionStart hook for Claude Code on the web.
#
# Purpose: every web session runs in a fresh, ephemeral container. The project
# design skills under .claude/skills/ are committed to the repo, so they load
# automatically on clone. The "impeccable" plugin, however, lives in ~/.claude/
# (outside the repo) and is wiped with each new container — so we (re)install it
# here. Idempotent and non-interactive; safe to run on every session.
#
# All progress goes to stderr so it does not pollute the session context.
set -u

# Only run in Claude Code on the web. Locally, leave the user's ~/.claude alone.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

log() { echo "[session-start] $*" >&2; }

# The Claude CLI drives the plugin system; bail out gracefully if it is absent.
if ! command -v claude >/dev/null 2>&1; then
  log "WARN: 'claude' CLI not on PATH; skipping impeccable plugin setup"
  exit 0
fi

# 1) Ensure the impeccable marketplace is registered (clones via git).
if claude plugin marketplace list 2>/dev/null | grep -qi "impeccable"; then
  log "impeccable marketplace already registered"
else
  log "adding impeccable marketplace (pbakaus/impeccable)..."
  claude plugin marketplace add pbakaus/impeccable 1>&2 || log "WARN: marketplace add failed"
fi

# 2) Ensure the impeccable plugin is installed + enabled (user scope).
if claude plugin list 2>/dev/null | grep -qi "impeccable@impeccable"; then
  log "impeccable plugin already installed"
else
  log "installing impeccable@impeccable..."
  claude plugin install impeccable@impeccable 1>&2 || log "WARN: plugin install failed"
fi

# 3) Ensure the official Claude marketplace + Vercel plugin are present.
if claude plugin marketplace list 2>/dev/null | grep -qi "claude-plugins-official"; then
  log "official marketplace already registered"
else
  log "adding official Claude marketplace..."
  claude plugin marketplace add anthropics/claude-plugins-official 1>&2 || log "WARN: marketplace add failed"
fi

if claude plugin list 2>/dev/null | grep -qi "vercel@claude-plugins-official"; then
  log "vercel plugin already installed"
else
  log "installing vercel@claude-plugins-official..."
  claude plugin install vercel@claude-plugins-official 1>&2 || log "WARN: plugin install failed"
fi

log "done"
exit 0
