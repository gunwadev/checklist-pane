---
description: Open or refresh the checklist sidebar pane for this folder
---

# /checklist — checklist sidebar

Opens a narrow herdr pane beside this session showing `checklist.json` as a
live checklist. Re-running it replaces the existing sidebar for this tab
rather than stacking a second one.

## Input

`$ARGUMENTS` may contain:

- **a folder or file path** — which checklist to show. Default: the current
  working directory.
- **`close`** — close this tab's sidebar and stop.

## Steps

1. If the arguments say close, run `checklist --close` and stop.

2. Work out the target folder from the arguments, defaulting to the current
   working directory. Resolve it to an absolute path.

3. Check whether `<target>/checklist.json` exists.

   If it does not, build one before opening the pane:

   - If `<target>` has a context file, read its next-actions list. The heading
     is `## Next actions` in converted folders and `## Next Steps` in older
     ones; match case-insensitively and take items up to the next `##`.
     Note the filesystem is case-insensitive, so `context.md` and `CONTEXT.md`
     are the same file.
   - **Skip items that are already finished** — struck through with `~~`, or
     carrying a done/resolved/answered marker. They are history, and the pane
     is for what is next. This is the same rule the state-file convention
     applies, so an old-format file yields only its live work.
   - Older files often have several competing lists (`Next Steps`, then
     `Immediate`, then `Then`). Merge them, drop duplicates, keep the order
     they appear in. If more than 10 live items survive, take the first 10 and
     say which ones you left out.
   - Use each action as `text`, and its trailing or parenthetical detail as
     `note`, trimmed to one short line.
   - If there is no context file and no next-actions list, ask the user what
     should be on the list. Do not invent items.

   Write it as:

   ```json
   {
     "title": "<folder name>",
     "items": [
       { "text": "first thing", "note": "one line of why or where", "done": false }
     ]
   }
   ```

   Keep `note` to one short line; it is shown under NEXT in a narrow pane.

4. Run `checklist <target>` and report the pane id it prints.

## Notes

- The pane re-reads the file whenever it changes, so editing `checklist.json`
  updates the sidebar with no restart. Toggle an item yourself with `space`,
  or ask for it and edit the JSON.
- `CHECKLIST_RATIO` sets the sidebar's share of the width, default `0.28`.
- Requires a herdr pane. Outside herdr, run `python3 checklist.py <target>`.
