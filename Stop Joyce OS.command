#!/bin/bash
# Double-click in Finder to stop JOYCE OS.
cd "$(dirname "$0")" || exit 1
bash "bin/joyce-stop.sh"
echo ""
echo "You can close this window."
