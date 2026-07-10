# tw93 Agent Guide

## Project

This repository powers the GitHub profile README and related generated profile content.

Deploy surface: pushing `main` is production. `README.md` is the live GitHub profile immediately, and `index.html` auto-deploys to `hi.tw93.fun` via Vercel on push. There is no staging.

## Repository Map

- `README.md` - generated profile README content.
- `build_readme.py` - README generation script.
- `requirements.txt` - Python dependencies for the generator.
- `.github/workflows/build.yml` - scheduled or manual workflow for README updates.
- `images/` - profile images.
- `index.html` - simple profile landing page.

## Commands

```bash
python3 build_readme.py
pip install -r requirements.txt
```

Use a virtual environment if installing dependencies locally. `build_readme.py` reads `GH_TOKEN` for GitHub API calls and falls back where possible when external feeds fail.

## Working Rules

- Preserve the generated marker comments in `README.md`; workflows update content between those markers.
- Do not manually rewrite generated sections unless the generator is updated too.
- Keep external API usage and tokens in GitHub Actions secrets or local environment, not in tracked files.
- Keep image paths stable unless all references are updated.

## Verification

- Generator changes: run `python3 build_readme.py` and inspect the README diff.
- Workflow changes: check `.github/workflows/build.yml` syntax and required secrets.
- Scheduled workflow changes: preserve the six-hour README refresh unless the maintainer asks to change cadence.
- Documentation-only changes: check links.

## GitHub Operations

- Use `gh` for issue, PR, and workflow inspection.
- Do not post public comments unless the maintainer explicitly asks.
