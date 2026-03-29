#!/usr/bin/env python3
"""
generate_resume_pdf.py

Converts content/_index.md to a 2-page PDF matching kevinsohn_resume_2026_g.pdf style.
Uses Chrome headless for rendering (no GTK/Pango required).

  • Removes avatar image
  • Replaces "About Me" heading with inline summary paragraph
  • Auto-scales font size (binary search) to guarantee ≤ 2 pages

Usage:
    python generate_resume_pdf.py [output.pdf]

Default output: content/kevinsohn_resume_generated.pdf
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
CONTENT_FILE = SCRIPT_DIR / "content" / "_index.md"
DEFAULT_OUTPUT = SCRIPT_DIR / "content" / "kevinsohn_resume_generated.pdf"

RESUME_NAME = "Kevin Sohn"

MAX_PAGES = 2
FONT_SIZE_MAX = 11.5   # pt — try here first
FONT_SIZE_MIN = 4.0    # pt — hard floor
SEARCH_TOL   = 0.03    # pt — stop binary search when range is this narrow

# Chrome executable (Windows)
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Chromium\Application\chrome.exe",
]


def find_chrome() -> str:
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    raise FileNotFoundError(
        "Chrome not found. Install Chrome or set CHROME_PATH env var."
    )


CHROME = os.environ.get("CHROME_PATH") or find_chrome()


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------
def read_md_body(md_file: Path) -> str:
    """Strip TOML front-matter (+++ … +++) and return the markdown body."""
    text = md_file.read_text(encoding="utf-8")
    if text.startswith("+++"):
        parts = text.split("+++", 2)
        return parts[2].strip() if len(parts) >= 3 else text.strip()
    return text.strip()


def transform_content(md_text: str) -> tuple[str, str, str]:
    """
    Split the markdown body into:
        email        — contact email string
        summary_html — "About Me" paragraph rendered to HTML (no heading, no avatar)
        rest_html    — everything from "Areas of Expertise" onward

    Hugo shortcodes are removed; the avatar figure is discarded.
    """
    md = MarkdownIt()

    # Drop Hugo shortcodes like {{< figure ... >}}
    md_text = re.sub(r"\{\{<[^>]*>\}\}", "", md_text)

    lines = md_text.split("\n")

    # Extract email: first non-blank, non-heading line
    email = ""
    body_start = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith("#"):
            email = s
            body_start = i + 1
            break

    # Separate "About Me" block from the rest
    summary_lines: list[str] = []
    rest_lines:    list[str] = []
    in_about_me   = False

    for line in lines[body_start:]:
        if re.match(r"^#+\s+About\s+Me\s*$", line, re.IGNORECASE):
            in_about_me = True
            continue

        if in_about_me:
            if re.match(r"^#+\s+\S", line):   # next section heading
                in_about_me = False
                rest_lines.append(line)
            else:
                summary_lines.append(line)
        else:
            rest_lines.append(line)

    summary_html = md.render("\n".join(summary_lines).strip())
    rest_html    = md.render("\n".join(rest_lines).strip())

    return email, summary_html, rest_html


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------
def build_html(
    email: str,
    summary_html: str,
    rest_html: str,
    font_size: float,
) -> str:
    name_pt   = font_size * 2.05
    h1_pt     = font_size * 1.70   # section headings
    h4_pt     = font_size * 1.00   # company names
    h5_pt     = font_size * 1.00   # job titles
    email_pt  = font_size * 0.95

    email_href = f"mailto:{email}" if not email.startswith("mailto:") else email

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inconsolata:wght@400;700&display=swap');

@page {{
    size: letter;
    margin: 0.60in 0.70in 0.50in 0.70in;
}}

*, *::before, *::after {{
    font-family: 'Inconsolata', 'Courier New', monospace;
    font-size: {font_size:.4f}pt;
    line-height: 1.22;
    color: #222222;
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    hyphens: none;
    -webkit-hyphens: none;
    word-break: keep-all;
    overflow-wrap: normal;
}}

body {{ background: white; }}

/* ---- Header ---- */
.resume-header {{ margin-bottom: 4pt; }}

.resume-name {{
    display: block;
    font-size: {name_pt:.4f}pt;
    font-weight: bold;
    line-height: 1.1;
    margin-bottom: 2pt;
}}

.resume-email {{
    font-size: {email_pt:.4f}pt;
    margin-bottom: 4pt;
    display: block;
}}
.resume-email a {{ color: #dc3545; text-decoration: none; }}

/* ---- Summary ---- */
.summary p {{
    font-size: {font_size:.4f}pt;
    margin-bottom: 5pt;
}}

/* ---- Section headings (h1) ---- */
h1 {{
    font-size: {h1_pt:.4f}pt;
    font-weight: bold;
    margin: 5pt 0 2.5pt 0;
    line-height: 1.15;
    page-break-after: avoid;
}}

/* ---- Company (h4) ---- */
h4 {{
    font-size: {h4_pt:.4f}pt;
    font-weight: bold;
    margin: 3.5pt 0 0.5pt 0;
    page-break-after: avoid;
}}

/* ---- Job title (h5) ---- */
h5 {{
    font-size: {h5_pt:.4f}pt;
    font-weight: bold;
    margin: 0 0 0.5pt 0;
    page-break-after: avoid;
}}

/* ---- Dates & other paragraphs ---- */
p {{ font-size: {font_size:.4f}pt; margin-bottom: 1.5pt; }}

/* ---- Bullet lists ---- */
ul {{
    margin: 1pt 0 3.5pt 0;
    padding-left: 14pt;
}}
li {{
    font-size: {font_size:.4f}pt;
    list-style-type: disc;
    margin-bottom: 0.8pt;
}}

/* ---- Job-entry separator ---- */
hr {{
    border: none;
    border-top: 1px solid #cccccc;
    margin: 2.5pt 0;
}}

</style>
</head>
<body>

<div class="resume-header">
    <span class="resume-name">{RESUME_NAME}</span>
    <span class="resume-email"><a href="{email_href}">{email}</a></span>
</div>

<div class="summary">
{summary_html}
</div>

<div id="content">
{rest_html}
</div>


</body>
</html>"""


# ---------------------------------------------------------------------------
# Chrome headless rendering
# ---------------------------------------------------------------------------
def html_to_pdf(html: str, pdf_path: Path) -> None:
    """Write HTML to a temp file, render to PDF via Chrome headless.

    Security notes:
    - Temp file is created in a private temp directory and deleted in a
      finally block regardless of success or failure.
    - pdf_path has already been validated by the caller (validate_output_path).
    - subprocess is called with a list (never shell=True) to prevent injection.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="resume_pdf_"))
    tmp_html = tmp_dir / "resume.html"
    try:
        # Write with restricted permissions where supported (no-op on Windows)
        tmp_html.write_text(html, encoding="utf-8")
        try:
            tmp_html.chmod(0o600)
        except NotImplementedError:
            pass  # Windows does not support POSIX chmod

        # Build a proper file:// URL (Windows needs forward-slash triplet)
        file_url = "file:///" + tmp_html.as_posix().lstrip("/")

        subprocess.run(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-extensions",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=10000",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path.resolve()}",
                file_url,
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
    finally:
        # Always clean up temp files
        tmp_html.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            pass


def count_pdf_pages(pdf_path: Path) -> int:
    """Return the number of pages in a PDF file."""
    return len(PdfReader(str(pdf_path)).pages)


# Target page dimensions: match the reference PDF (A3 paper, 841.9 × 1191.1 pt).
# The reference was generated at A3 size, so at 100% zoom in any browser it
# appears 37% larger than a standard US-Letter PDF.  We scale our Letter output
# up to A3 so both files look identical at 100%.
TARGET_WIDTH_PT  = 841.9
TARGET_HEIGHT_PT = 1191.1


def scale_and_set_zoom(pdf_path: Path, zoom: float = 1.0) -> None:
    """Scale every page to TARGET dimensions and embed a fixed initial zoom.

    Why two operations in one pass:
      1. Scale  — Chrome generates at US Letter (612 × 792 pt); the reference
                  PDF is A3 (841.9 × 1191.1 pt).  Uniform scaling to A3 width
                  (×1.376) makes content appear the same size at 100% zoom.
                  Height is scaled by a slightly different ratio (×1.504) to
                  reach true A3, which is a ~9 % vertical stretch — barely
                  perceptible in a monospace resume font.
      2. Zoom   — Bakes /OpenAction so the viewer opens at exactly `zoom`
                  instead of its own default ('fit-to-window').
    """
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, NameObject, NullObject, NumberObject

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for page in reader.pages:
        orig_w = float(page.mediabox.width)
        orig_h = float(page.mediabox.height)
        sx = TARGET_WIDTH_PT  / orig_w
        sy = TARGET_HEIGHT_PT / orig_h
        page.scale(sx, sy)
        writer.add_page(page)

    # /OpenAction: open at page 1, same position, explicit zoom
    open_action = ArrayObject([
        writer.pages[0],
        NameObject("/XYZ"),
        NullObject(),           # left  — unchanged
        NullObject(),           # top   — unchanged
        NumberObject(zoom),     # 1.0 = 100%
    ])
    writer._root_object[NameObject("/OpenAction")] = open_action

    with open(str(pdf_path), "wb") as f:
        writer.write(f)


# ---------------------------------------------------------------------------
# Auto-scaling
# ---------------------------------------------------------------------------
def generate_pdf(
    md_file:     Path = CONTENT_FILE,
    output_path: Path = DEFAULT_OUTPUT,
    verbose:     bool = True,
) -> None:
    if verbose:
        print(f"Source : {md_file}")
        print(f"Output : {output_path}")
        print(f"Chrome : {CHROME}")

    md_body = read_md_body(md_file)
    email, summary_html, rest_html = transform_content(md_body)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- Quick check at maximum font size ----
    html = build_html(email, summary_html, rest_html, FONT_SIZE_MAX)
    html_to_pdf(html, output_path)
    pages = count_pdf_pages(output_path)

    if verbose:
        print(f"  Max font {FONT_SIZE_MAX:.2f}pt → {pages} page(s)")

    if pages <= MAX_PAGES:
        if verbose:
            print(f"  Fits at max size — done.")
        return

    # ---- Binary search for largest font that fits in MAX_PAGES ----
    lo, hi = FONT_SIZE_MIN, FONT_SIZE_MAX
    best_size = FONT_SIZE_MIN

    for i in range(30):
        mid = (lo + hi) / 2
        html = build_html(email, summary_html, rest_html, mid)
        html_to_pdf(html, output_path)
        pages = count_pdf_pages(output_path)

        if verbose:
            print(f"  [{i+1:2d}] {mid:.4f}pt → {pages} page(s)")

        if pages <= MAX_PAGES:
            best_size = mid
            lo = mid
        else:
            hi = mid

        if hi - lo < SEARCH_TOL:
            break

    # ---- Final render at best_size ----
    html = build_html(email, summary_html, rest_html, best_size)
    html_to_pdf(html, output_path)
    final_pages = count_pdf_pages(output_path)
    scale_and_set_zoom(output_path, zoom=1.0)  # match A3 size + open at 100%

    if verbose:
        print(f"\nDone: {final_pages} page(s) at {best_size:.4f}pt → {output_path}")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def validate_output_path(raw: str) -> Path:
    """Resolve and sanity-check a user-supplied output path.

    Prevents path-traversal: rejects paths that escape the project root OR
    that don't end in '.pdf'.  Raises ValueError with a human-readable message
    so the caller can print it and exit cleanly.
    """
    try:
        resolved = Path(raw).resolve()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid output path: {raw!r}") from exc

    if resolved.suffix.lower() != ".pdf":
        raise ValueError(
            f"Output path must end in '.pdf', got: {raw!r}"
        )

    # Warn (but don't block) if the path escapes the project tree — the owner
    # of this local tool may intentionally want to write elsewhere.
    project_root = SCRIPT_DIR.resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError:
        print(
            f"WARNING: output path is outside the project directory:\n"
            f"  {resolved}\n"
            f"  Proceeding — press Ctrl-C within 3 s to abort.",
            file=sys.stderr,
        )
        import time; time.sleep(3)

    return resolved


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        out = validate_output_path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    generate_pdf(output_path=out)
