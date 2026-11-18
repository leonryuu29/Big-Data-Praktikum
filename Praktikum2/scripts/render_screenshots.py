"""Rendert die aufgezeichneten cqlsh-Sitzungen (results/*_session.txt) als Terminal-PNGs.

Die Bilder zeigen 1:1 den Text, den cqlsh tatsächlich ausgegeben hat (siehe record_session.py);
es wird nichts nachbearbeitet. Benötigt Playwright mit Chromium.
Aufruf:  python scripts/render_screenshots.py results docs/screenshots
"""
import glob
import html
import os
import re
import sys

from playwright.sync_api import sync_playwright

CSS = """
body{margin:0;background:#1e1e1e}
.win{margin:16px;border-radius:8px;overflow:hidden;box-shadow:0 4px 16px #0008;display:inline-block;min-width:900px}
.bar{background:#323233;color:#ccc;font:13px system-ui,sans-serif;padding:7px 12px}
.bar b{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px}
pre{margin:0;padding:14px 18px;background:#0c0c0c;color:#d4d4d4;font:13px/1.45 'DejaVu Sans Mono',monospace;white-space:pre}
.p{color:#4ec9b0}.e{color:#f48771}.ok{color:#b5cea8}
"""


def colorize(text):
    out = []
    for line in text.split("\n"):
        h = html.escape(line)
        if re.match(r"cqlsh(:\w+)?> |   \.\.\. ", line):
            h = f'<span class="p">{h}</span>'
        elif "Error" in line or "Exists" in line:
            h = f'<span class="e">{h}</span>'
        elif re.search(r"rows imported|^\(\d+ rows\)", line):
            h = f'<span class="ok">{h}</span>'
        out.append(h)
    return "\n".join(out)


def main(src="results", dst="docs/screenshots"):
    os.makedirs(dst, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, "*_session.txt")))
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(device_scale_factor=2)
        for f in files:
            name = os.path.basename(f).replace("_session.txt", "")
            text = open(f, encoding="utf-8").read().rstrip()
            doc = (f"<style>{CSS}</style><div class='win'><div class='bar'><b style='background:#ff5f56'></b>"
                   f"<b style='background:#ffbd2e'></b><b style='background:#27c93f'></b>"
                   f"docker exec -it CassandraPraktikum2026 cqlsh &nbsp;·&nbsp; {name}</div>"
                   f"<pre>{colorize(text)}</pre></div>")
            page.set_content(doc)
            page.locator(".win").screenshot(path=os.path.join(dst, name + ".png"))
            print("->", os.path.join(dst, name + ".png"))
        b.close()


if __name__ == "__main__":
    main(*sys.argv[1:])
