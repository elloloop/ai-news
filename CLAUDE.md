# CLAUDE.md

## How I expect you to write code

**No shortcuts. "Simple" never means "sloppy."** A small diff that hardcodes,
duplicates, or skips a test isn't simpler — it's deferred cost.

1. **Fix causes, not symptoms.** Find the root cause before fixing. If you're
   applying a workaround, say so explicitly and explain why. Never swallow an
   exception or silence an error to make a problem disappear.

2. **Think about consequences.** Before changing shared or widely-used code,
   trace its callers and the invariants they rely on. A fix that's locally
   correct but breaks something elsewhere — now or later — is not a fix.

3. **SOLID, sensibly.** One responsibility per class/widget/function. Separate
   pure logic from I/O so it can be tested. Inject dependencies that cross a
   boundary so they're mockable. Don't add abstractions for things that don't
   cross a boundary.

4. **DRY about knowledge, not appearance.** Don't duplicate a rule or decision.
   Code that merely looks similar but changes for different reasons stays
   separate. When unsure, prefer duplication over a premature/wrong abstraction.

5. **No hardcoded values.** No magic numbers or strings inline — give them
   names. Environment/tenant/feature-specific values go in typed config in
   application code, never scattered literals, never the database.

6. **Readable & maintainable.** Clear names, short flat functions, early
   returns over deep nesting. Comments explain *why*, not *what*. Match the
   existing style of the file you're editing.

7. **Testable, and prove it.** Ship a test for behavior you add or change. If
   something is hard to test, that's a design smell — restructure until it
   isn't. "Works but can't be tested" means it isn't done.

A change is done only when: the cause (not a symptom) is fixed, no new hardcoded
values, a test covers it, and the analyzer/formatter are clean.

## Project facts

> Keep these current as the repo evolves; only write what you've confirmed.

- **Setup command:** `pip install -r scripts/requirements.txt`
- **Analyze/lint command:** _TBD_
- **Test command (all):** _TBD_
- **Test command (single):** _TBD_
- **Format command:** _TBD_
- **Run an app:** `python scripts/fetch_feeds.py` (fetch RSS into `content/articles/*.md`) then `python scripts/build_site.py` (render `_site/`)
- **Repo layout:** `scripts/` (fetch + build Python), `templates/` (Jinja2 HTML), `static/` (CSS, favicon), `content/articles/` (generated Markdown posts), `feeds.yml` (RSS sources), `.github/workflows/` (CI), `_site/` (build output, gitignored)
- **State management / data layer:** No database. Articles are Markdown files with YAML frontmatter under `content/articles/`; RSS sources defined in `feeds.yml`. Build reads Markdown, renders static HTML to `_site/`
- **Generated files NOT to hand-edit:** `_site/` (build output, gitignored); `content/articles/*.md` are auto-fetched/committed by the Fetch & Build workflow
- **Other gotchas:** Python 3.12 in CI; deploys to GitHub Pages; `Fetch & Build` runs on a 6-hour cron and commits new articles back to `main`; Claude summarization is optional and only runs when `ANTHROPIC_API_KEY` is set (otherwise falls back to the RSS description); fetch skips entries older than 7 days
