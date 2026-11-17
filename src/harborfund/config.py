"""Project paths and constants shared by every task.

Import from here instead of hard-coding paths or years:

    from harborfund.config import RAW_DIR, BASE_YEAR

The project root is found automatically (the folder holding pyproject.toml
and data/). Set the HARBORFUND_ROOT environment variable to override it.
"""

from __future__ import annotations

import os
from pathlib import Path


def _find_root() -> Path:
    env = os.environ.get("HARBORFUND_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # Editable install / running from the repo: walk up from this file,
    # then from the working directory (covers notebooks/ and non-editable installs).
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for p in (start, *start.parents):
            if (p / "pyproject.toml").is_file() and (p / "data").is_dir():
                return p
    raise RuntimeError(
        "Could not find the project root. Run from inside the repo or set HARBORFUND_ROOT."
    )


# --- Paths -----------------------------------------------------------------
ROOT: Path = _find_root()
DATA_DIR: Path = ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"  # downloads, untouched; not in git
PROCESSED_DIR: Path = DATA_DIR / "processed"  # derived from raw by code; not in git
REFERENCE_DIR: Path = DATA_DIR / "reference"  # hand-built lookup tables; in git
MANIFEST_PATH: Path = DATA_DIR / "manifest.csv"  # one row per downloaded file
NOTEBOOKS_DIR: Path = ROOT / "notebooks"
DOCS_DIR: Path = ROOT / "docs"

PROGRAM_INVENTORY_PATH: Path = REFERENCE_DIR / "program_inventory.csv"  # filled by T0.3

# --- Dollars ---------------------------------------------------------------
# All dollar amounts are reported in constant 2025 dollars, deflated with CPI-U.
BASE_YEAR: int = 2025
# BLS CPI-U, U.S. city average, all items, not seasonally adjusted.
CPI_SERIES_ID: str = "CUUR0000SA0"
# Not yet decided: whether to average CPI by calendar year or federal fiscal
# year. The task that writes the deflator decides and logs it.

# --- Time ------------------------------------------------------------------
# Federal fiscal year N runs 1 Oct (N-1) to 30 Sep N.
FISCAL_YEAR_START_MONTH: int = 10
# Study window per the project plan (~FY2010-FY2026).
STUDY_FY_START: int = 2010
STUDY_FY_END: int = 2026


def fiscal_year(year: int, month: int) -> int:
    """Federal fiscal year for a calendar year and month (Oct-Dec roll forward)."""
    return year + 1 if month >= FISCAL_YEAR_START_MONTH else year
