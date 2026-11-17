# data/

Three folders, three rules. Code reads paths from `harborfund.config`, never hard-coded strings.

| Folder | What goes here | In git? | Who writes it | Can it be regenerated? |
|---|---|---|---|---|
| `raw/` | Files exactly as downloaded (USAspending pulls, ERDC extracts, FOIA returns, PacFIN, Census…) | **No.** Only `.gitkeep` placeholders | Download scripts in `src/harborfund/` | Yes, by re-downloading. Every file gets a row in `manifest.csv` |
| `processed/` | Anything derived from `raw/` (cleaned tables, linked awards, the harbor × fiscal-year panel) | **No** | Code in `src/harborfund/` or numbered notebooks | Yes, by re-running the code. Never edit by hand |
| `reference/` | Hand-built lookup tables: program inventory, harbor ↔ entity ↔ UEI crosswalk, other curated mappings | **Yes**, versioned | People, or a documented script whose inputs are themselves tracked | **No.** Never overwritten from raw data. Changes go through git so they can be reviewed |

## raw/

- Never edit a raw file. If it needs fixing, fix it in code on the way to `processed/`.
- Organize by source: `raw/<source>/…`, e.g. `raw/usaspending/`, `raw/erdc/`, `raw/foia/marad/`. Add a `.gitkeep` so the folder exists on a fresh clone.
- Log every downloaded file in `data/manifest.csv` (tracked): source ID, URL, retrieval time (UTC), sha256, license, notes. Data tasks also report source URLs, download dates and row counts in their handoff (plan, Conventions).
- FOIA returns may contain material that shouldn't be public. Keep them in `raw/foia/` (ignored) and check before anything derived from them lands in `reference/`.

## processed/

- Rebuildable from `raw/` + `reference/` + code. If you can't rebuild it, it belongs in `reference/` instead.
- Dollar columns are in constant 2025 dollars (CPI-U) unless the column name says otherwise (e.g. `_nominal`). Years are federal fiscal years unless named otherwise.
- Shared releases (Zenodo, T4.2) are built from here, not committed here.

## reference/

- Each table has a `source` column or a companion note (`<table>_sources.md`) saying where every row came from.
- Edited by hand or by a documented script. Record non-trivial edits in the commit message.
- Harbor IDs come from the fishing-port access-gaps inventory. The harbor ↔ entity crosswalk is the only link between harbors and recipient entities.

Current tables:

| File | Owner task | Status |
|---|---|---|
| `program_inventory.csv` | T0.3 | Placeholder, header only. T0.3 fills it and may change the columns |

## manifest.csv

Tracked in git. One row per file in `raw/`. Columns match the port project: `source_id,url,retrieved_utc,sha256,license,notes`.
