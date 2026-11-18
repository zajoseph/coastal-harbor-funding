"""Snapshot the public DOT/MARAD applicant lists (task T2.5a).

    uv run python -m harborfund.ingest.applicants              # download everything
    uv run python -m harborfund.ingest.applicants --only dot_infra
    uv run python -m harborfund.ingest.applicants --dry-run    # list files, no network
    uv run python -m harborfund.ingest.applicants --import-dir ~/Downloads   # files saved by hand

The DOT and MARAD sites answered every scripted request with HTTP 403 on 2026-11-18, so in
practice the files are saved by hand in a browser and registered with --import-dir, which
copies them in, checksums them and logs them with "method": "browser".

Each file lands in data/raw/applicants/<source>/<YYYY-MM-DD>/ exactly as served, next to
a copy of the landing page that links to it (`_page_<name>.html`, kept for the page's
"Last updated" date). Every file gets a row in data/manifest.csv. Notes (JSON) carry the
task, local path, bytes, row counts per sheet, the landing page and, where T0.4 recorded
a checksum on 2026-11-17, whether the file has changed since.

Profiling (fields, Pacific counts, quirks) is in notebooks/03_applicant_lists_profile.ipynb;
nothing here parses the lists beyond counting rows.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from harborfund import config
from harborfund.ingest.usaspending import append_manifest, rel, sha256

TASK = "T2.5a"
OUT_DIR = config.RAW_DIR / "applicants"
LICENSE_NOTE = "U.S. government work (DOT/MARAD website); terms of use not checked"
DOT = "https://www.transportation.gov"
BUILDAMERICA = DOT + "/buildamerica/sites/buildamerica.dot.gov/files"


@dataclass(frozen=True)
class SourceFile:
    source: str  # folder under data/raw/applicants/
    name: str  # short id, used in --only and notes
    url: str
    page: str  # landing page that links to the file
    rounds: str  # what the file covers, as published
    t04_sha256: str | None = None  # checksum T0.4 recorded on 2026-11-17, if any
    extra: dict = field(default_factory=dict)


FILES: list[SourceFile] = [
    SourceFile(
        "marad_pidp",
        "pidp_fy19_26",
        "https://www.maritime.dot.gov/sites/marad.dot.gov/files/2026-10/"
        "FY19-26%20PIDP%20Eligible%20Applicants.xlsx",
        "https://www.maritime.dot.gov/grants-finances/federal-grant-assistance/pidp-applicant-list",
        "PIDP FY2019-FY2026 eligible applications",
        "6d910c1c8a1200ad6319aab2c0b734533d3e496bca1e2838a307d9e982df4191",
    ),
    SourceFile(
        "dot_tiger_build",
        "tiger2009_build2025",
        DOT + "/sites/dot.gov/files/2025-07/"
        "TIGER%202009%20-%20BUILD%202025%20Eligible%20Applications.xlsx",
        DOT + "/policy-initiatives/tiger/tiger-application-list",
        "TIGER 2009 - BUILD 2025 Round 2 eligible applications",
        "70ec6e0efd0999b287aa97572f36baadb9bcb3cee7975a1047545d49cfff6bc9",
    ),
    # INFRA FY2022+ (spreadsheets). T0.4 opened the FY2022 workbook and FY23-24 only.
    SourceFile(
        "dot_infra",
        "usdot_fy2022_discretionary",
        DOT + "/sites/dot.gov/files/2023-04/"
        "FY%202022%20USDOT%20Discretionary%20Grant%20Applicant%20List.xlsx",
        DOT + "/grants/dot-navigator/list-bil-discretionary-grant-applications",
        "FY2022 BUILD/INFRA/Mega/other BIL rounds (INFRA sheet)",
    ),
    SourceFile(
        "dot_infra",
        "infra_fy22",
        DOT + "/sites/dot.gov/files/2023-03/INFRA%20FY22%20Applications.xlsx",
        DOT + "/grants/infra/infra-fy22-applications",
        "INFRA FY2022 applications",
    ),
    SourceFile(
        "dot_infra",
        "infra_fy23_24",
        DOT + "/sites/dot.gov/files/2024-03/INFRA%20FY23-24%20Applications.xlsx",
        DOT + "/grants/INFRA%20FY%202023-2024%20Applications",
        "INFRA FY2023-2024 applications",
    ),
    SourceFile(
        "dot_infra",
        "infra_fy25_26",
        DOT + "/sites/dot.gov/files/2025-05/INFRA%20Applications%2025-26.xlsx",
        DOT + "/policy-initiatives/infra/infra-fy-2025-26-applications",
        "INFRA FY2025-2026 applications",
    ),
    SourceFile(
        "dot_infra",
        "infra_fy26",
        DOT + "/sites/dot.gov/files/2026-10/INFRA%20FY26%20Applications%20%281%29.xlsx",
        DOT + "/policy-initiatives/infra/infra-fy-26-applications",
        "INFRA FY2026 applications (page updated 2026-10-23)",
    ),
    # FASTLANE/INFRA FY2016-FY2021 (PDFs), linked from "INFRA - Project Applications".
    *[
        SourceFile(
            "dot_infra",
            name,
            f"{BUILDAMERICA}/{path}",
            DOT + "/grants/infra-project-applications",
            rounds,
        )
        for name, path, rounds in [
            ("infra_fy21", "2021-06/INFRA%202021%20Application%20List.pdf", "INFRA FY2021"),
            ("infra_fy20", "2020-06/INFRA%202020%20Application%20List.pdf", "INFRA FY2020"),
            ("infra_fy19", "2019-08/infra-2019-application-list.pdf", "INFRA FY2019"),
            ("infra_fy17_18", "2019-08/infra-2017-2018-applicationlist.pdf", "INFRA FY2017-18"),
            ("fastlane_fy17", "2019-08/fastlane2017applications.pdf", "FASTLANE FY2017"),
            ("fastlane_fy16", "2019-08/fastlane2016applications27oct.pdf", "FASTLANE FY2016"),
        ]
    ],
]

MAGIC = {".xlsx": b"PK\x03\x04", ".pdf": b"%PDF"}


def filename(url: str) -> str:
    from urllib.parse import unquote

    return unquote(url.rsplit("/", 1)[-1])


def page_last_updated(html: str) -> str | None:
    m = re.search(r"Last updated:\s*(?:<[^>]+>\s*)*([^<]+)", html)
    return m.group(1).strip() if m else None


def xlsx_rows(path: Path) -> dict[str, int]:
    """Non-empty rows per sheet, minus one header row. Approximate: some sheets have
    title rows above the header; the notebook counts records properly."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        n = sum(1 for row in ws.iter_rows(values_only=True) if any(v is not None for v in row))
        out[ws.title] = max(n - 1, 0)
    wb.close()
    return out


def pdf_pages(path: Path) -> int | None:
    try:
        from pypdf import PdfReader  # optional; not a project dependency
    except ImportError:
        return None
    return len(PdfReader(str(path)).pages)


def _session():
    import requests

    s = requests.Session()
    s.headers.update({"User-Agent": "harborfund (github.com/zajoseph/coastal-harbor-funding)"})
    return s


def download(run_date: str, only: list[str] | None, force: bool, dry_run: bool) -> list[dict]:
    todo = [f for f in FILES if not only or f.name in only or f.source in only]
    if dry_run:
        for f in todo:
            print(f"{f.source:16} {f.name:28} {f.url}")
        return []
    s = _session()
    pages: dict[str, str] = {}
    report = []
    failed: list[str] = []
    for f in todo:
        d = OUT_DIR / f.source / run_date
        d.mkdir(parents=True, exist_ok=True)
        dest = d / filename(f.url)
        if dest.exists() and not force:
            print(f"skip (exists): {rel(dest)}")
            continue
        if f.page not in pages:
            try:
                r = s.get(f.page, timeout=60)
                r.raise_for_status()
                pages[f.page] = r.text
                slug = re.sub(r"[^A-Za-z0-9]+", "_", f.page.split("//", 1)[1]).strip("_")[-60:]
                (d / f"_page_{slug}.html").write_text(r.text, encoding="utf-8")
            except OSError as e:  # requests errors are OSErrors; the page is context only
                print(f"warning: landing page not saved ({f.page}): {e}")
                pages[f.page] = ""
        retrieved = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        ext = dest.suffix.lower()
        try:
            r = s.get(f.url, timeout=120)
            r.raise_for_status()
            if ext in MAGIC and not r.content.startswith(MAGIC[ext]):
                raise RuntimeError(f"not a {ext} file (starts {r.content[:40]!r})")
        except (OSError, RuntimeError) as e:
            print(f"FAILED {f.name}: {e}")
            failed.append(f.name)
            continue
        dest.write_bytes(r.content)
        digest = sha256(dest)
        notes = {
            "task": TASK,
            "source": f.source,
            "name": f.name,
            "rounds": f.rounds,
            "file": rel(dest),
            "bytes": dest.stat().st_size,
            "page": f.page,
            "page_last_updated": page_last_updated(pages[f.page]) if pages[f.page] else None,
            "content_type": r.headers.get("content-type"),
        }
        if ext == ".xlsx":
            rows = xlsx_rows(dest)
            notes["rows_by_sheet"] = rows
            notes["rows"] = sum(rows.values())
        elif ext == ".pdf":
            notes["pages"] = pdf_pages(dest)
        if f.t04_sha256:
            notes["t04_sha256"] = f.t04_sha256
            notes["changed_since_t04"] = digest != f.t04_sha256
        append_manifest(
            [
                {
                    "source_id": f"applicants_{f.source}",
                    "url": f.url,
                    "retrieved_utc": retrieved,
                    "sha256": digest,
                    "license": LICENSE_NOTE,
                    "notes": json.dumps(notes, separators=(",", ":"), sort_keys=True),
                }
            ]
        )
        flag = ""
        if f.t04_sha256:
            flag = "  CHANGED since T0.4" if notes["changed_since_t04"] else "  same as T0.4"
        print(f"{f.name:28} {notes['bytes']:>10,} B  sha256 {digest[:12]}…{flag}")
        report.append(notes | {"sha256": digest})
    if failed:
        print(f"\n{len(failed)} file(s) failed: {', '.join(failed)}")
    return report


def find_local(f: SourceFile, folder: Path) -> Path | None:
    """The browser-saved copy of a file: exact name, or the name with a ' (1)'-style suffix."""
    name = filename(f.url)
    exact = folder / name
    if exact.exists():
        return exact
    stem, ext = Path(name).stem, Path(name).suffix
    hits = sorted(folder.glob(f"{glob_escape(stem)}*{ext}"), key=lambda p: p.stat().st_mtime)
    return hits[-1] if hits else None


def glob_escape(s: str) -> str:
    return re.sub(r"([\[\]*?])", r"[\1]", s)


def import_files(folder: Path, run_date: str, only: list[str] | None, force: bool) -> list[dict]:
    """Register files saved by hand in a browser (the DOT/MARAD sites refuse scripted
    requests with HTTP 403). Copies each into data/raw/applicants/<source>/<date>/ under
    the published file name and logs it like a scripted download, with
    `"method": "browser"` in the notes. The retrieval time is the saved file's
    modification time."""
    import shutil

    todo = [f for f in FILES if not only or f.name in only or f.source in only]
    report, missing = [], []
    for f in todo:
        src = find_local(f, folder)
        if src is None:
            missing.append(f.name)
            continue
        ext = src.suffix.lower()
        head = src.open("rb").read(8)
        if ext in MAGIC and not head.startswith(MAGIC[ext]):
            print(f"SKIP {f.name}: {src.name} is not a {ext} file (starts {head!r})")
            missing.append(f.name)
            continue
        d = OUT_DIR / f.source / run_date
        d.mkdir(parents=True, exist_ok=True)
        dest = d / filename(f.url)
        if dest.exists() and not force:
            print(f"skip (exists): {rel(dest)}")
            continue
        shutil.copy2(src, dest)
        digest = sha256(dest)
        retrieved = dt.datetime.fromtimestamp(src.stat().st_mtime, dt.UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        notes = {
            "task": TASK,
            "source": f.source,
            "name": f.name,
            "rounds": f.rounds,
            "file": rel(dest),
            "bytes": dest.stat().st_size,
            "page": f.page,
            "method": "browser",
            "method_note": "saved by hand in a browser; the site returns HTTP 403 to scripts",
            "browser_file_name": src.name,
        }
        if ext == ".xlsx":
            rows = xlsx_rows(dest)
            notes["rows_by_sheet"] = rows
            notes["rows"] = sum(rows.values())
        elif ext == ".pdf":
            notes["pages"] = pdf_pages(dest)
        if f.t04_sha256:
            notes["t04_sha256"] = f.t04_sha256
            notes["changed_since_t04"] = digest != f.t04_sha256
        append_manifest(
            [
                {
                    "source_id": f"applicants_{f.source}",
                    "url": f.url,
                    "retrieved_utc": retrieved,
                    "sha256": digest,
                    "license": LICENSE_NOTE,
                    "notes": json.dumps(notes, separators=(",", ":"), sort_keys=True),
                }
            ]
        )
        flag = ""
        if f.t04_sha256:
            flag = "  CHANGED since T0.4" if notes["changed_since_t04"] else "  same as T0.4"
        print(f"{f.name:28} {notes['bytes']:>10,} B  sha256 {digest[:12]}…{flag}")
        report.append(notes | {"sha256": digest})
    if missing:
        print(f"\nnot found in {folder}: {', '.join(missing)}")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m harborfund.ingest.applicants")
    ap.add_argument("--date", default=None, help="Run folder date (default: today, UTC)")
    ap.add_argument("--only", nargs="*", default=None, help="File names or source folders")
    ap.add_argument("--force", action="store_true", help="Re-download files that exist")
    ap.add_argument("--dry-run", action="store_true", help="List files without downloading")
    ap.add_argument(
        "--import-dir",
        type=Path,
        default=None,
        help="Register files already saved by hand in this folder (e.g. ~/Downloads) instead of downloading",
    )
    a = ap.parse_args(argv)
    run_date = a.date or dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    if a.import_dir:
        import_files(a.import_dir.expanduser(), run_date, a.only, a.force)
    else:
        download(run_date, a.only, a.force, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
