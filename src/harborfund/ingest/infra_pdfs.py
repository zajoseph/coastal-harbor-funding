"""Read DOT's FASTLANE/INFRA application-list PDFs (FY2016-FY2021) into tables (task T2.5a).

DOT published these rounds only as PDFs printed from Excel: one row per application with
#, project name, applicant organization, state ("CA: California"), the request and one or
two cost columns. Long names wrap onto several lines.

Method: word boxes from poppler's `pdftotext -bbox`. Each record is anchored on its
row-number cell (one line). Words left of the state column go to the nearest anchor: nearest by
vertical distance when the sheet centres wrapped cells, nearest at-or-above when it
top-aligns them (detected per page). State, request and cost columns are reliable
(row counts equal the last row number in every file). `name_text` (project name and
applicant together, in reading order) is a heuristic: wrapped lines can land on the
neighbouring row and the two columns are not separated.

Needs `pdftotext` on the PATH (macOS: `brew install poppler`). Notebook 03 uses it for
counts and the Pacific rows; T2.5b should still eyeball Pacific names before linking.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

WORD_RE = re.compile(
    r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>'
)
PAGE_RE = re.compile(r"<page [^>]*>(.*?)</page>", re.DOTALL)
STATE_CODE = re.compile(r"^[A-Z]{2}:$")
HEADER_WORDS = {"Applicant", "State"}

PDF_ROUNDS = {
    "fastlane2016applications27oct.pdf": "FASTLANE FY2016",
    "fastlane2017applications.pdf": "FASTLANE FY2017",
    "infra-2017-2018-applicationlist.pdf": "INFRA FY2017-18",
    "infra-2019-application-list.pdf": "INFRA FY2019",
    "INFRA 2020 Application List.pdf": "INFRA FY2020",
    "INFRA 2021 Application List.pdf": "INFRA FY2021",
}


def have_pdftotext() -> bool:
    return shutil.which("pdftotext") is not None


def _pages(path: Path) -> list[pd.DataFrame]:
    out = subprocess.run(
        ["pdftotext", "-bbox", str(path), "-"], check=True, capture_output=True, text=True
    ).stdout
    pages = []
    for body in PAGE_RE.findall(out):
        w = pd.DataFrame(
            [
                (float(a), float(b), float(c), float(d), html.unescape(t))
                for a, b, c, d, t in WORD_RE.findall(body)
            ],
            columns=["x0", "y0", "x1", "y1", "text"],
        )
        w["yc"] = (w["y0"] + w["y1"]) / 2
        pages.append(w)
    return pages


def parse_application_pdf(path: Path, round_label: str) -> pd.DataFrame:
    rows = []
    for pno, w in enumerate(_pages(path), start=1):
        if w.empty:
            continue
        codes = w[w["text"].str.match(STATE_CODE)]
        if codes.empty:
            continue
        state_x0 = codes["x0"].min() - 2
        lh = float((codes["y1"] - codes["y0"]).mean())
        # header band: the first line holding "Applicant" (or "State"), plus a wrapped
        # second header line just below it; body text starts after that
        head = w[w["text"].isin(HEADER_WORDS) & (w["y1"] < codes["y0"].min())]
        if head.empty:
            top = codes["y0"].min() - 1
        else:
            h0 = head["y0"].min()
            band = w[(w["y0"] >= h0 - 0.5 * lh) & (w["y0"] <= h0 + 1.6 * lh)]
            top = min(band["y1"].max(), codes["y0"].min() - 1)
        body = w[(w["y0"] > top + 1) & (w["y0"] <= codes["y1"].max() + 3 * lh)]
        left = body[body["x1"] <= state_x0 + 1]
        nums = left[left["text"].str.fullmatch(r"\d{1,3}") & (left["x0"] < left["x0"].min() + 15)]
        text = left[~left.index.isin(nums.index)]
        # Row anchors: the # cells (one line, at the row's text line). State cells are not
        # always on the same baseline (FY2017-18 pages 3-6 sit ~11 px higher), so the state
        # is taken as the nearest state code within a line height and a half.
        anchors = (nums if len(nums) >= 0.8 * len(codes) else codes).sort_values("yc")
        ay = anchors["yc"].to_numpy()
        centred = bool((text["yc"] < ay[0] - 0.6 * lh).any())
        recs: dict[int, list[str]] = {i: [] for i in range(len(ay))}
        for r in text.sort_values(["yc", "x0"]).itertuples():
            if centred:
                i = int(abs(ay - r.yc).argmin())
            else:
                above = [k for k in range(len(ay)) if ay[k] <= r.yc + 0.6 * lh]
                i = above[-1] if above else 0
            recs[i].append(r.text)
        money_w = body[body["text"].str.match(r"^\$[\d,]+$") & (body["x0"] > state_x0)]
        for i, a in enumerate(anchors.itertuples()):
            dy = (codes["yc"] - a.yc).abs()
            st = codes.loc[dy.idxmin(), "text"][:2] if dy.min() < 1.5 * lh else None
            line = money_w[(money_w["yc"] - a.yc).abs() < 0.6 * lh].sort_values("x0")
            money = [float(t.replace("$", "").replace(",", "")) for t in line["text"]]
            rows.append(
                {
                    "round": round_label,
                    "row_no": int(a.text) if a.text.isdigit() else None,
                    "name_text": " ".join(recs[i]),
                    "state": st,
                    "request": money[0] if money else None,
                    "cost_col2": money[1] if len(money) > 1 else None,
                    "cost_col3": money[2] if len(money) > 2 else None,
                    "page": pno,
                    "layout": "centred" if centred else "top",
                    "file": path.name,
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["row_no"] = df["row_no"].astype("Int64")
    return df


def read_all(folder: Path) -> pd.DataFrame:
    frames = [
        parse_application_pdf(folder / n, lab)
        for n, lab in PDF_ROUNDS.items()
        if (folder / n).exists()
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
