"""Erzeugt Abgabe.pdf (und optional TESTBERICHT.pdf) aus den Markdown-Dateien.

Benötigt: pip install markdown playwright && playwright install chromium
Aufruf:   python scripts/build_pdf.py Abgabe.md TESTBERICHT.md
"""
import os
import sys

import markdown
from playwright.sync_api import sync_playwright

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font: 10.5pt/1.45 'DejaVu Sans', Arial, sans-serif; color: #1a1a1a; }
h1 { font-size: 18pt; border-bottom: 2px solid #1a1a1a; padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 14pt; margin-top: 18pt; border-bottom: 1px solid #bbb; padding-bottom: 2px; page-break-after: avoid; }
h3 { font-size: 12pt; margin-top: 12pt; page-break-after: avoid; }
h4 { font-size: 10.5pt; margin-top: 10pt; page-break-after: avoid; }
code { font: 8.6pt 'DejaVu Sans Mono', monospace; background: #f3f3f3; padding: 0 2px; }
pre { background: #f6f6f6; border: 1px solid #ddd; padding: 6px 8px; overflow: hidden; white-space: pre-wrap;
      font-size: 8pt; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9pt; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 3px 5px; vertical-align: top; text-align: left; }
th { background: #eee; }
img { max-width: 100%; border: 1px solid #ccc; margin: 4pt 0; page-break-inside: avoid; }
"""


def build(md_path):
    base = os.path.dirname(os.path.abspath(md_path))
    text = open(md_path, encoding="utf-8").read()
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    html = f"<!doctype html><meta charset='utf-8'><style>{CSS}</style><body>{body}</body>"
    tmp = os.path.join(base, "._build.html")
    open(tmp, "w", encoding="utf-8").write(html)
    out = os.path.splitext(md_path)[0] + ".pdf"
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto("file://" + tmp)
        page.pdf(path=out, format="A4", print_background=True,
                 display_header_footer=True, header_template="<span></span>",
                 footer_template="<div style='font-size:8pt;width:100%;text-align:center;color:#777'>"
                                 "Zhaoze Yu · 50293014 · Big Data, 2. Praktikum · Seite <span class='pageNumber'></span>"
                                 " / <span class='totalPages'></span></div>",
                 margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"})
        b.close()
    os.remove(tmp)
    print("->", out)


if __name__ == "__main__":
    for f in sys.argv[1:] or ["Abgabe.md"]:
        build(f)
