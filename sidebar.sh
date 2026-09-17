#!/usr/bin/env bash
# Open a checklist in a sidebar pane beside the current one.
#
# Usage: sidebar.sh [folder-or-file]
#        sidebar.sh --close        close the sidebar belonging to this tab
set -euo pipefail

here=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
program="$here/checklist.py"

close_only=false
if [ "${1:-}" = "--close" ] || [ "${1:-}" = "-c" ]; then
  close_only=true
  shift
fi

target=${1:-$PWD}
[ -e "$target" ] && target=$(readlink -f "$target")

if [ "${HERDR_ENV:-}" != "1" ]; then
  echo "Not inside a herdr pane. Run it directly instead:" >&2
  echo "  python3 $program $target" >&2
  exit 1
fi

# A sidebar already open in this tab, if any. Panes are renamed to a fixed
# label on launch, so this does not depend on the process title appearing.
LABEL="checklist"
existing=$(herdr pane list | LABEL="$LABEL" python3 -c '
import json, os, sys
tab = os.environ.get("HERDR_TAB_ID")
label = os.environ.get("LABEL")
for pane in json.load(sys.stdin)["result"]["panes"]:
    if pane.get("tab_id") != tab:
        continue
    title = pane.get("terminal_title_stripped") or pane.get("terminal_title") or ""
    if pane.get("label") == label or "checklist.py" in title:
        print(pane["pane_id"])
        break')

if [ -n "$existing" ]; then
  herdr pane close "$existing" >/dev/null 2>&1 || true
  if [ "$close_only" = true ]; then
    echo "closed the checklist sidebar ($existing)"
    exit 0
  fi
elif [ "$close_only" = true ]; then
  echo "no checklist sidebar open in this tab"
  exit 0
fi

# herdr's --ratio is the share kept by the pane being split, so invert it.
width=${CHECKLIST_RATIO:-0.28}
ratio=$(python3 -c "print(round(1 - float('$width'), 4))")

pane=$(herdr pane split --current --direction right --ratio "$ratio" --cwd "$target" \
  | python3 -c '
import json, sys
def find(node):
    if isinstance(node, dict):
        if isinstance(node.get("pane_id"), str):
            return node["pane_id"]
        for value in node.values():
            found = find(value)
            if found:
                return found
    if isinstance(node, list):
        for value in node:
            found = find(value)
            if found:
                return found
    return None
print(find(json.load(sys.stdin)) or "", end="")')

if [ -z "$pane" ]; then
  echo "could not read the new pane id from herdr" >&2
  exit 1
fi

herdr pane rename "$pane" "$LABEL" >/dev/null 2>&1 || true
herdr pane run "$pane" python3 "$program" "$target" >/dev/null
echo "checklist sidebar open in $pane"
