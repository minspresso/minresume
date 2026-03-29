# CLAUDE.md — Project Context for Claude Code Sessions

## Project Overview
Kevin (Min) Sohn's personal resume website + local PDF generator.
- **Live site:** https://minresu.me
- **GitHub:** https://github.com/minspresso/minresume
- **Local path:** `D:\www\minresume`

---

## Stack

| Layer | Technology |
|---|---|
| Static site generator | Hugo 0.123.8 (extended) |
| Theme | `researcher` (at `themes/researcher/`) |
| Font | Inconsolata (Google Fonts) |
| Hosting | Azure Static Web Apps (2 regions) + Firebase Hosting |
| CI/CD | GitHub Actions → push to `main` auto-deploys |
| PDF generator | `generate_resume_pdf.py` (Python, Chrome headless) |

---

## Key Files

```
D:\www\minresume\
├── content/
│   ├── _index.md                     ← PRIMARY resume source (edit this)
│   ├── contact.md                    ← Contact page
│   ├── tpm.md                        ← Alternate About page
│   ├── avatar.jpg                    ← Profile photo (used on website only)
│   └── kevinsohn_resume_2026_i.pdf   ← Current published PDF (linked in nav)
├── generate_resume_pdf.py            ← Local PDF converter (see below)
├── config.toml                       ← Hugo config, nav menu, site title
├── themes/researcher/                ← Active Hugo theme
│   ├── assets/sass/researcher.scss   ← Main stylesheet
│   └── assets/sass/variables.scss    ← Theme variables ($max-width, $avatar-size, etc.)
├── .github/workflows/
│   └── two_swas_one_firebase.yaml    ← CI/CD: build Hugo → deploy to Azure + Firebase
├── firebase.json                     ← Firebase hosting config (public dir: public/)
└── .gitignore                        ← Excludes: .claude/, .tmpdeps/, __pycache__/, etc.
```

---

## Deployment Pipeline

Push to `main` → GitHub Actions triggers automatically:
1. `hugo --minify` → builds to `/public`
2. Deploy to **Azure SWA - Mango Wave** (region 1)
3. Deploy to **Azure SWA - Wonderful Mushroom** (region 2)
4. Deploy to **Firebase Hosting** (project: `minresu-me`, channel: live)

All secrets are stored in GitHub Actions secrets — never hardcoded:
- `AZURE_STATIC_WEB_APPS_API_TOKEN_MANGO_WAVE_09FB0F41E`
- `AZURE_STATIC_WEB_APPS_API_TOKEN_WONDERFUL_MUSHROOM_02A817D10`
- `FIREBASE_SERVICE_ACCOUNT`
- `GITHUB_TOKEN` (auto-provided)

---

## Local PDF Generator

**Script:** `generate_resume_pdf.py`
**Dependencies:** `markdown-it-py`, `pypdf` (both pip-installed)
**Requires:** Chrome at `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
  (override with `CHROME_PATH` env var)

### Usage
```bash
# Default output: content/kevinsohn_resume_generated.pdf
python generate_resume_pdf.py

# Custom output
python generate_resume_pdf.py content/kevinsohn_resume_2026_i.pdf
```

### How it works
1. Reads `content/_index.md`, strips Hugo front-matter
2. Removes Hugo shortcodes (avatar figure discarded)
3. Drops "About Me" heading — summary paragraph appears inline under name/email
4. Renders name as `Kevin Sohn` (PDF display name, not "Kevin (Min) Sohn")
5. No footer (website footer stripped for clean PDF)
6. Binary-searches font size (4–11.5pt) to guarantee content fits in **exactly 2 pages**
7. Chrome headless renders HTML → US Letter PDF (8.5 × 11 in / 612 × 792 pt)
8. `pypdf` post-processes: embeds `/OpenAction` at 100% zoom so PDF opens at actual size

### Key constants (top of script)
```python
RESUME_NAME   = "Kevin Sohn"       # Name shown in PDF header
MAX_PAGES     = 2                  # Hard page limit
FONT_SIZE_MAX = 11.5               # Start here, shrink if needed
FONT_SIZE_MIN = 4.0                # Absolute floor
```

### Output location
`content/kevinsohn_resume_generated.pdf` is in `.gitignore` — commit manually
when ready to publish (rename to the versioned filename, e.g. `kevinsohn_resume_2026_j.pdf`).

---

## Workflow: Updating the Resume

1. Edit `content/_index.md`
2. Run `python generate_resume_pdf.py` → review output PDF
3. When happy, copy/rename to `content/kevinsohn_resume_YYYY_x.pdf`
4. Update `config.toml` → `url = "/kevinsohn_resume_YYYY_x.pdf"`
5. Commit & push → GitHub Actions auto-deploys

---

## Git Conventions
- Work directly on `main` (no PR required for this solo project)
- Commit message style: short imperative subject + body with bullet details
- Co-author line: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- Never commit: `.claude/`, `.tmpdeps/`, `content/kevinsohn_resume_generated.pdf`

---

## Security Notes (audit completed 2026-03-28)
- All deployment secrets via `${{ secrets.* }}` — nothing hardcoded
- `generate_resume_pdf.py`: path traversal guard (`validate_output_path()`), temp files
  in private `mkdtemp()` dir with `chmod 0o600`, always cleaned in `finally`
- `.gitignore` covers: Python artifacts, generated PDF, OS/editor noise, `.env*`, secrets

---

## Site Content Structure (`_index.md`)
```
Email (codenism@gmail.com)
# About Me          ← heading stripped in PDF; avatar shortcode removed
  {{< figure >}}    ← avatar (website only)
  [summary text]    ← becomes inline summary in PDF
# Areas of Expertise
# Professional Experience
  #### > Company    ← h4
  ##### Job Title   ← h5
  Date
  + bullet points
  ---               ← hr separator between jobs
# Certification
# Publications
# Education & Training
# Awards
```
