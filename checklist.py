#!/usr/bin/env python3
"""Render a JSON checklist in a narrow terminal pane.

Keys: j/k move, space toggle, g/G top/bottom, r reload, q quit.
The file is re-read whenever it changes on disk, so an agent editing it
updates the pane without a restart.
"""

import curses
import json
import os
import sys
import tempfile
import textwrap

DEFAULT_NAME = "checklist.json"
POLL_MS = 400


def resolve(arg):
    path = arg or os.environ.get("CHECKLIST_FILE") or DEFAULT_NAME
    if os.path.isdir(path):
        path = os.path.join(path, DEFAULT_NAME)
    return os.path.abspath(path)


def normalize(raw, path):
    """A bare list of strings is a valid checklist; so is {title, items}."""
    if isinstance(raw, list):
        raw = {"items": raw}
    if not isinstance(raw, dict):
        raise ValueError("checklist must be a JSON object or array")
    raw.setdefault("items", [])
    if not raw.get("title"):
        raw["title"] = os.path.basename(os.path.dirname(path)) or "Checklist"
    return raw


def view(raw):
    out = []
    for item in raw["items"]:
        if isinstance(item, str):
            out.append({"text": item, "done": False, "note": ""})
        else:
            out.append({
                "text": str(item.get("text", "")),
                "done": bool(item.get("done")),
                "note": str(item.get("note") or ""),
            })
    return out


class Checklist:
    def __init__(self, path):
        self.path = path
        self.mtime = 0.0
        self.error = ""
        self.raw = {"title": "Checklist", "items": []}
        self.load()

    def stamp(self):
        try:
            return os.stat(self.path).st_mtime
        except OSError:
            return 0.0

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                self.raw = normalize(json.load(fh), self.path)
            self.error = ""
        except FileNotFoundError:
            self.error = "no checklist.json here"
            self.raw = {"title": "Checklist", "items": []}
        except (ValueError, OSError) as exc:
            self.error = str(exc)[:200]
        self.mtime = self.stamp()

    def changed(self):
        return self.stamp() != self.mtime

    def toggle(self, index):
        """Refuse the write if the file moved under us; reload instead."""
        if self.changed():
            self.load()
            return "reloaded, toggle skipped"
        items = self.raw["items"]
        if not 0 <= index < len(items):
            return ""
        item = items[index]
        if isinstance(item, str):
            items[index] = {"text": item, "done": True}
        else:
            item["done"] = not bool(item.get("done"))
        return self.save()

    def save(self):
        directory = os.path.dirname(self.path) or "."
        try:
            fd, tmp = tempfile.mkstemp(dir=directory, prefix=".checklist-", suffix=".tmp")
            payload = {k: v for k, v in self.raw.items() if not k.startswith("_")}
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp, self.path)
            self.mtime = self.stamp()
            return ""
        except OSError as exc:
            return f"write failed: {exc}"


def wrap(text, width):
    return textwrap.wrap(text, max(8, width)) or [""]


def draw(stdscr, data, items, cursor, top, status, path):
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    inner = max(8, width - 2)
    done = sum(1 for i in items if i["done"])
    nxt = next((n for n, i in enumerate(items) if not i["done"]), None)
    row = 0

    def put(text, attr=0, indent=1):
        nonlocal row
        if row < height - 1:
            stdscr.addnstr(row, indent, text, max(0, width - indent - 1), attr)
            row += 1

    put(data["title"][:inner], curses.A_BOLD)
    if items:
        filled = round((done / len(items)) * (inner - 8))
        bar = "█" * filled + "░" * max(0, inner - 8 - filled)
        put(f"{bar} {done}/{len(items)}", curses.color_pair(1))
    row += 1

    if data.get("_error") and row < height - 3:
        for line in wrap(data["_error"], inner):
            put(line, curses.color_pair(2) | curses.A_BOLD)
        put("")
        for line in wrap("create checklist.json here, or pass a path", inner):
            put(line, curses.A_DIM)
    elif nxt is not None and row < height - 4:
        put("NEXT", curses.color_pair(3) | curses.A_BOLD)
        for line in wrap(items[nxt]["text"], inner):
            put(line, curses.A_BOLD)
        if items[nxt]["note"]:
            for line in wrap(items[nxt]["note"], inner - 2):
                put("  " + line, curses.A_DIM)
        row += 1
    elif items and nxt is None:
        put("all done", curses.color_pair(1) | curses.A_BOLD)
        row += 1

    if row < height - 1:
        stdscr.hline(row, 1, curses.ACS_HLINE, inner)
        row += 1

    list_top = row
    space = max(1, height - 1 - list_top)
    for offset in range(space):
        index = top + offset
        if index >= len(items):
            break
        item = items[index]
        mark = "[x]" if item["done"] else "[ ]"
        attr = curses.color_pair(1) | curses.A_DIM if item["done"] else 0
        if index == nxt:
            attr = curses.color_pair(3) | curses.A_BOLD
        prefix = "▸" if index == cursor else " "
        if index == cursor:
            attr |= curses.A_REVERSE
        text = item["text"].replace("\n", " ")
        stdscr.addnstr(list_top + offset, 0, f"{prefix}{mark} {text}", width - 1, attr)

    footer = status or ("j/k  space  r  q" if not data.get("_err") else "")
    if len(items) > space:
        footer = f"{footer}  {top + 1}-{min(top + space, len(items))}/{len(items)}"
    stdscr.addnstr(height - 1, 0, footer[: width - 1], width - 1, curses.A_DIM)
    stdscr.refresh()


def run(stdscr, path):
    curses.curs_set(0)
    curses.use_default_colors()
    for pair, fg in ((1, curses.COLOR_GREEN), (2, curses.COLOR_RED), (3, curses.COLOR_YELLOW)):
        try:
            curses.init_pair(pair, fg, -1)
        except curses.error:
            pass
    stdscr.timeout(POLL_MS)

    book = Checklist(path)
    cursor = top = 0
    status = ""

    while True:
        items = view(book.raw)
        if book.error:
            items = []
        cursor = max(0, min(cursor, max(0, len(items) - 1)))
        height = stdscr.getmaxyx()[0]
        space = max(1, height - 10)
        top = max(0, min(top, max(0, len(items) - 1)))
        if cursor < top:
            top = cursor
        elif cursor >= top + space:
            top = cursor - space + 1

        book.raw["_error"] = book.error
        draw(stdscr, book.raw, items, cursor, top, status or book.error, path)

        try:
            key = stdscr.getch()
        except KeyboardInterrupt:
            return

        if key == -1:
            if book.changed():
                book.load()
                status = ""
            continue

        status = ""
        if key in (ord("q"), 27):
            return
        if key in (ord("j"), curses.KEY_DOWN):
            cursor += 1
        elif key in (ord("k"), curses.KEY_UP):
            cursor -= 1
        elif key == ord("g"):
            cursor = 0
        elif key == ord("G"):
            cursor = len(items) - 1
        elif key in (ord(" "), ord("\n"), curses.KEY_ENTER, 10, 13):
            status = book.toggle(cursor)
        elif key == ord("r"):
            book.load()


def main():
    path = resolve(sys.argv[1] if len(sys.argv) > 1 else None)
    try:
        curses.wrapper(run, path)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
