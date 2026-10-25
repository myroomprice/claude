#!/usr/bin/env python3
"""Build the results page the skill opens: page/results.html with its fonts baked in.

Browsers won't load font files into a page opened straight from disk, and the page should
make no outside requests, so the fonts go inside the page as data. Edit page/results.html,
then run:  python3 tools/build_page.py
"""

import base64
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "page", "results.html")
TARGET = os.path.join(ROOT, "plugins", "myroomsearch", "skills", "myroomsearch", "assets", "results.html")
# Cloudflare serves docs/ (see wrangler.jsonc), so the published app lives at https://myroomsearch.com/
PAGES = os.path.join(ROOT, "docs", "index.html")
NOTE = "<!-- Built by tools/build_page.py from page/results.html. Edit that file, not this one. -->\n"


def build():
    with open(SOURCE, encoding="utf-8") as f:
        html = f.read()

    def inline(match):
        path = os.path.join(ROOT, "page", match.group(1))
        with open(path, "rb") as font:
            data = base64.b64encode(font.read()).decode("ascii")
        return 'url("data:font/woff2;base64,' + data + '")'

    html, count = re.subn(r'url\("(fonts/[\w.-]+\.woff2)"\)', inline, html)
    if count == 0:
        sys.exit("No fonts found to inline; check page/results.html.")

    def inline_image(match):
        path = os.path.join(ROOT, "page", match.group(2))
        with open(path, "rb") as image:
            data = base64.b64encode(image.read()).decode("ascii")
        kind = {"png": "png", "webp": "webp", "jpg": "jpeg", "jpeg": "jpeg"}[match.group(2).rsplit(".", 1)[1].lower()]
        return '%s="data:image/%s;base64,%s"' % (match.group(1), kind, data)

    html, images = re.subn(r'(src|href)="(brand/[\w.-]+\.(?:png|webp|jpe?g))"', inline_image, html)

    def inline_logo(match):
        with open(os.path.join(ROOT, "page", match.group(1)), "rb") as logo:
            return '"data:image/png;base64,%s"' % base64.b64encode(logo.read()).decode("ascii")

    # The site logos the page's script refers to by name.
    html, logos = re.subn(r'"(brand/sites/[\w.-]+\.png)"', inline_logo, html)
    images += logos
    return html.replace("<!doctype html>\n", "<!doctype html>\n" + NOTE, 1), count + images


def main():
    html, count = build()
    if "--check" in sys.argv:
        for path in (TARGET, PAGES):
            with open(path, encoding="utf-8") as f:
                if f.read() != html:
                    sys.exit("%s is out of date: run tools/build_page.py" % os.path.relpath(path, ROOT))
        return
    for path in (TARGET, PAGES):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    print("Built %s and %s (%d fonts and images, %d KB)" % (os.path.relpath(TARGET, ROOT), os.path.relpath(PAGES, ROOT), count, len(html) // 1024))

if __name__ == "__main__":
    main()
