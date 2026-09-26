#!/bin/bash
# Installs all insureMO skills for Claude Code on the web.
# Skill dirs in .claude/skills are symlinks into ~/.insuremo/skills-store, which
# does not survive between containers, so they are reinstalled each session.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

npm config set "@insuremo:registry" https://public.insuremo.com/artifactory/api/npm/npm
npx -y @insuremo/skills-tool add insuremo-skills --all -a claude-code -y >&2

# --all also links skills for many other agents; drop those dirs as long as
# they hold nothing but symlinks (never touch real files).
for d in .adal .agents .augment .bob .codebuddy .commandcode .continue .cortex \
         .crush .factory .goose .iflow .junie .kilocode .kiro .kode .mcpjam .mux \
         .neovate .openhands .pi .pochi .qwen .roo .vibe .windsurf .zencoder skills; do
  if [ -d "$d" ] && [ -z "$(find "$d" -not -type d -not -type l -print -quit)" ]; then
    rm -rf "$d"
  fi
done

# Make every insureMO skill manual-only: Claude won't pick one on its own, it
# runs only when the user invokes it (e.g. /insuremo-deep-search).
for name in $(node -e 'console.log(Object.keys(require("./skills-lock.json").skills).join("\n"))'); do
  f=".claude/skills/$name/SKILL.md"
  if [ -f "$f" ] && ! grep -q '^disable-model-invocation:' "$f"; then
    sed -i '1s/^---$/---\ndisable-model-invocation: true/' "$f"
  fi
done
