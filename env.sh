#!/bin/bash
# Environment for ask-s3df skill.
# Site-specific config goes in env.local (not tracked in git).
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [[ -f "$SKILL_DIR/env.local" ]]; then
    source "$SKILL_DIR/env.local"
fi
export SDF_DOCS_ROOT="${SDF_DOCS_ROOT:-}"
