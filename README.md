# checklist-pane

A checklist that lives in a folder as `checklist.json` and renders in a narrow
terminal pane beside the work it belongs to. It shows what is next with a
one-line explanation, scrolls, and toggles with the keyboard.

It re-reads the file whenever it changes, so a coding agent editing the
checklist updates the pane with no restart.

```
 my-project
 ████████████████░░░░░░░░░░░ 3/5

 NEXT
 Launcher that splits a pane
   two calls: split, then run

 ─────────────────────────────
 [x] Render a JSON checklist
 [x] Reload when the file changes
 [x] Toggle items with space
▸[ ] Launcher that splits a pane
 [ ] Try it against a real list
```

## Install

Requires Python 3. No packages.

```bash
git clone https://github.com/<you>/checklist-pane.git
ln -s "$PWD/checklist-pane/sidebar.sh" ~/.local/bin/checklist
```

For the Claude Code command, copy `commands/checklist.md` into
`~/.claude/commands/`. Then `/checklist` opens a sidebar for the current
folder, building `checklist.json` from the folder's context file if there
isn't one yet.

## Use

```bash
checklist                 # sidebar for the current folder
checklist /some/path      # sidebar for another folder
checklist --close         # close this tab's sidebar
```

| Key | |
|---|---|
| `j` / `k` | move |
| `space` | toggle |
| `g` / `G` | first / last |
| `r` | reload |
| `q` | quit |

`CHECKLIST_RATIO` sets the sidebar's share of the width, default `0.28`.

## The file

A bare array of strings is valid:

```json
["first thing", "second thing"]
```

So is the full shape, where `note` is the line shown under NEXT:

```json
{
  "title": "my-project",
  "items": [
    { "text": "first thing", "note": "one line of why or where", "done": false }
  ]
}
```

Unknown keys survive a write. Writes are atomic, and are refused if the file
changed on disk since it was read, so an agent and a keypress cannot clobber
each other.

## Panes

`sidebar.sh` splits a pane using [herdr](https://herdr.dev). Without herdr the
display still works in any terminal — it is plain curses:

```bash
python3 checklist.py /some/folder
```

## Licence

MIT
