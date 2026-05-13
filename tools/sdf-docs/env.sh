#!/bin/bash
# Environment configuration for sdf-docs sync.
# Sources env.local for deployment-specific overrides.

# Add shared uv to PATH (needed for docs-index)
export PATH="/sdf/group/lcls/ds/dm/apps/dev/bin:$PATH"

# Use shared Python installs (not per-user ~/.local/share/uv/python)
export UV_PYTHON_INSTALL_DIR="/sdf/group/lcls/ds/dm/apps/dev/python"

export SDF_DOCS_APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SDF_DOCS_DATA_DIR="${SDF_DOCS_DATA_DIR:-/sdf/group/lcls/ds/dm/apps/dev/data/sdf-docs}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache-$USER}"

# Source env.local for deployment-specific overrides
if [[ -f "$SDF_DOCS_APP_DIR/env.local" ]]; then
    source "$SDF_DOCS_APP_DIR/env.local"
fi
