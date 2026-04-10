#!/bin/bash
# setup.sh — One-time local setup for ask-s3df
#
# Usage:
#   ./setup.sh [DATA_DIR]
#
# Clones the S3DF docs repo (prod branch), builds the FTS5 search index,
# and generates env.local so the skill is ready to use.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${1:-$HOME/.local/share/docs-skills/sdf-docs}"

if [[ -d "$DATA_DIR" ]]; then
    echo "Data directory already exists: $DATA_DIR"
    echo "To re-index, run: $SKILL_DIR/bin/docs-index index \"$DATA_DIR\" --incremental --ext md"
    exit 0
fi

echo "Cloning slaclab/sdf-docs (branch: prod) → $DATA_DIR ..."
mkdir -p "$(dirname "$DATA_DIR")"
git clone --branch prod https://github.com/slaclab/sdf-docs.git "$DATA_DIR"

echo "Building search index..."
"$SKILL_DIR/bin/docs-index" index "$DATA_DIR" --incremental --ext md

cat > "$SKILL_DIR/env.local" <<EOF
export SDF_DOCS_ROOT="$DATA_DIR"
export PATH="$SKILL_DIR/bin:\$PATH"
EOF

echo ""
echo "Done. Skill is ready to use."
echo "env.local created at: $SKILL_DIR/env.local"
