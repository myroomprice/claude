#!/usr/bin/env python3
"""Build the short copies of the browser scripts that Claude runs in web pages.

Claude has to type a script out in full every time it runs one, and typing is the slowest thing it does,
so the skill ships minified copies. Edit the readable sources in browser/, then run:
    python3 tools/build_scripts.py          (needs Node; uses terser)
    python3 tools/build_scripts.py --check  (fails if a built copy is out of date)
"""

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "browser")
TARGET = os.path.join(ROOT, "plugins", "myroomprice", "skills", "myroomprice", "scripts")
NAMES = ["find_pages", "watch_page", "load_rooms"]
# WANT stays readable: Claude puts the hotel's name in place of "HOTEL NAME".
TERSER = ["npx", "--yes", "terser@5.31.0", "--module", "--ecma", "2020", "-c", "passes=2", "-m", "reserved=['WANT']"]


def minify(name):
    with tempfile.TemporaryDirectory() as tmp:
        # As a module, so top-level await is allowed.
        src = os.path.join(tmp, name + ".mjs")
        with open(os.path.join(SOURCES, name + ".js"), encoding="utf-8") as f, open(src, "w", encoding="utf-8") as g:
            g.write(f.read())
        out = os.path.join(tmp, name + ".min.js")
        result = subprocess.run(TERSER + [src, "-o", out], capture_output=True, text=True)
        if result.returncode != 0:
            sys.exit("terser failed on %s:\n%s" % (name, result.stderr))
        with open(out, encoding="utf-8") as f:
            return f.read().strip() + "\n"


def main():
    check = "--check" in sys.argv
    for name in NAMES:
        code = minify(name)
        path = os.path.join(TARGET, name + ".js")
        if check:
            if not os.path.exists(path) or open(path, encoding="utf-8").read() != code:
                sys.exit("%s is out of date: run tools/build_scripts.py" % os.path.relpath(path, ROOT))
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        print("Built %s (%d characters)" % (os.path.relpath(path, ROOT), len(code)))


if __name__ == "__main__":
    main()
