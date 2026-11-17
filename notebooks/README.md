# notebooks/

## Naming

`NN_topic.ipynb`

- `NN`: two-digit number giving the run order (`01`, `02`, …). Numbers are never reused or renumbered once committed; leave gaps if you like.
- `topic`: lower-case snake_case, a few words, e.g. `01_usaspending_pilot.ipynb`, `02_crosswalk_pilot.ipynb`, `03_match_rate.ipynb`.
- First cell (markdown): title, task ID (e.g. T1.1), what the notebook reads and writes.

## Rules

- Notebooks explore and report; reusable logic lives in `src/harborfund/` and is imported.
- Read and write data only through paths in `harborfund.config`.
- Notebooks never write to `data/reference/`.
- Clear outputs before committing unless the outputs are the deliverable (say so in the first cell).
