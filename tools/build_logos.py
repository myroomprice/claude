#!/usr/bin/env python3
"""Render the MyRoomPrice logo PNGs from brand/logo.html with headless Chrome.

Transparent versions are trimmed to the logo's edges; the navy ones keep their fixed size.
Run:  python3 tools/build_logos.py
"""

import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND = os.path.join(ROOT, "brand")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# name: (window size, transparent?)
VERSIONS = {
    "horizontal-white-text": ((2000, 500), True),
    "horizontal-dark-text": ((2000, 500), True),
    "stacked-white-text": ((1400, 900), True),
    "stacked-dark-text": ((1400, 900), True),
    "horizontal-navy": ((1200, 400), False),
    "stacked-navy": ((1080, 1080), False),
    "icon-navy": ((512, 512), False),
}


def render(name, size, transparent):
    out = os.path.join(BRAND, "myroomprice-logo-%s.png" % name)
    cmd = [CHROME, "--headless=new", "--hide-scrollbars", "--allow-file-access-from-files",
           "--force-device-scale-factor=1", "--window-size=%d,%d" % size,
           "--screenshot=" + out, "file://%s#%s" % (os.path.join(BRAND, "logo.html"), name)]
    if transparent:
        cmd.insert(1, "--default-background-color=00000000")
    subprocess.run(cmd, check=True, capture_output=True, timeout=60)
    if transparent:
        img = Image.open(out)
        box = img.getbbox()
        if box:
            img.crop(box).save(out)
    return out


def main():
    if not os.path.exists(CHROME):
        sys.exit("Google Chrome isn't installed where expected: " + CHROME)
    for name, (size, transparent) in VERSIONS.items():
        out = render(name, size, transparent)
        w, h = Image.open(out).size
        print("%-28s %4d x %d" % (os.path.basename(out), w, h))


if __name__ == "__main__":
    main()
