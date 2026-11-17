# Coastal Harbor Funding Equity

> **Status:** setting up (Phase 0). Sections marked _TBD_ are filled in at later phases.

## Project question

Does federal and state harbor funding go to the places with the greatest **need**, or the greatest **capacity to apply** for it?

The core unit is Pacific Coast harbors from San Diego, CA to Bellingham, WA, using the harbor list from the [fishing-port access-gaps](https://github.com/zajoseph/fishing-port-access-gaps) project, over roughly FY2010–FY2026. Funding is studied in three channels: competitive grants (PIDP, BRIC, EDA Public Works, NOAA resilience, Sea Grant), USACE navigation and dredging spending, and Community Project Funding earmarks. State programs come in a later phase.

Planned outputs: a reproducible harbor × fiscal-year panel (Zenodo release) and a paper.

Project plan: [editable plan](https://claude.ai/artifact/GAviiQtiNBcv9m1Q4RVVeG) (collaborators only).

## Conventions

- Dollars in **constant 2025 dollars**, deflated with CPI-U (`harborfund.config.BASE_YEAR`, `CPI_SERIES_ID`).
- Years are **federal fiscal years** (FY N = Oct N-1 to Sep N) unless a column says otherwise.
- Harbor IDs come from the port inventory. The harbor ↔ entity crosswalk in `data/reference/` is the only harbor ↔ recipient link.

## Repository layout

```
coastal-harbor-funding/
├── data/
│   ├── README.md         # the rule for each folder (read this first)
│   ├── manifest.csv      # one row per downloaded file (tracked)
│   ├── raw/              # downloads as received (not in git)
│   ├── processed/        # derived from raw by code (not in git)
│   └── reference/        # hand-built lookup tables, versioned in git
│       └── program_inventory.csv
├── src/harborfund/       # Python package; config.py holds paths and constants
├── notebooks/            # numbered: 01_topic.ipynb, 02_… (see notebooks/README.md)
├── docs/                 # methods notes, codebook
├── tests/
├── pyproject.toml        # dependencies
└── uv.lock               # exact versions
```

## Setup

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) and git.

```bash
git clone https://github.com/zajoseph/coastal-harbor-funding.git
cd coastal-harbor-funding
uv sync                 # creates .venv/ with Python, the package (editable) and dev tools, from uv.lock
uv run pytest           # smoke test
uv run jupyter lab      # notebooks
```

To add a dependency: `uv add <package>` (or `uv add --dev <package>`), then commit `pyproject.toml` and `uv.lock` together.

Without uv: `python -m venv .venv && source .venv/bin/activate && pip install -e .` (unpinned; uv.lock is the reference).

## Reproduce

_TBD (Phase 2):_ download → process → panel run order.

## License

- Code: [MIT](LICENSE).
- Data tables in `data/reference/`, derived datasets and documentation: [CC BY 4.0](LICENSE-DATA.md).
- Third-party source data keeps its own terms; see `data/manifest.csv`.
