#!/bin/bash
# usage: push.sh function/UPX api/UPY ... (relative to src/dev/Tenant/UP_PRODUCTS_API)
cd /tmp/claude-0/-home-user-Tablet/4e5f48e0-1baf-5a1d-9f0f-ce844ee516ee/scratchpad/uponly-build/ic
for f in "$@"; do n=$(basename $f); printf "%-22s " $n; imo icomposer push current --profile portal:uponly src/dev/Tenant/UP_PRODUCTS_API/$f/$n.groovy 2>&1 | grep -E "Remote Saved|failed|Cannot|Static type" | head -4 | cut -c1-700 | tr '\n' ' '; echo; done
