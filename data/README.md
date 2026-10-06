# Dataset workspace

No tickets are seeded. A fresh deployment creates an empty SQLite database;
subsequent restarts retain tickets. All service submissions use `POST /tickets`.

Obtain the course CSV and actual team number from the course/team. Confirm the
row indexing convention: the extraction helper uses zero-based data rows,
excluding the header, and selects `team_number * 1000` through
`team_number * 1000 + 999`, inclusive. Pass the exact narrative column name.
The original course CSV is never modified. The team CSV must contain exactly
those 1,000 assigned rows and the columns `row,narrative`; `row` retains the
original zero-based data-row number. The course CSV is
`data/ict3113_tickets.csv` (50,000 rows; columns `row,source_label,narrative`).
This is team 7, so `data/team.csv` holds rows 7000-7999. CSV files are stored
byte-for-byte (`.gitattributes`: `*.csv -text`) so a Windows checkout cannot
change narratives and, with them, the reproducible selection.

```powershell
python scripts/extract_team_data.py data/course.csv data/team.csv --team-number <TEAM_NUMBER> --narrative-column "<COLUMN_NAME>"
python scripts/create_golden_set.py data/team.csv --team-number <TEAM_NUMBER> --count 180 --seed 3113 --output-dir data/labelling
```

The selector uses a documented SHA-256 ranking of seed, original row number,
and narrative, then sorts selected tickets by original row number. It writes a
selection manifest and two separate files, `annotator_a.csv` and
`annotator_b.csv`. Both sheets have identical `row,narrative` values and blank
`assigned_category,notes` cells. The selector rejects invalid row ranges,
duplicates, missing narratives, invalid counts, and existing outputs. It never
copies source labels. Give each annotator only their own sheet; do not merge or
share labels before both sheets are complete.

After both annotators finish, calculate agreement and create a blank-resolution
report:

```powershell
python -m scripts.agreement data/labelling/annotator_a.csv data/labelling/annotator_b.csv --disagreements data/labelling/disagreements.csv
```

The recorded result for the completed sheets, with the SHA-256 of each input
sheet, is kept in `results/accuracy/agreement.json`.

The command requires matching row numbers and narratives, and a valid category
for every ticket from both annotators. It reports total, agreed, disagreed, raw
percentage agreement, and unweighted Cohen's kappa. If expected agreement is
100%, kappa is mathematically undefined and is reported as `null`; no labels
means no result. The disagreement report includes only disagreements, with
`final_resolved_label`, `resolution_notes`, and `protocol_updated` blank.

Humans discuss each disagreement under the agreed protocol, fill all three
resolution fields, and update the protocol if agreed. Then create a new final
file:

```powershell
python -m scripts.finalize_golden_set data/labelling/annotator_a.csv data/labelling/annotator_b.csv data/labelling/disagreements.csv --output data/golden_set_final.csv
```

The finalizer checks matching sheets, valid and complete labels, exact
disagreement coverage, completed human resolutions, and the 150-200 ticket
count. It refuses to overwrite the output, including after it is frozen. Keep
the final golden set unchanged; protocol changes or replacement samples require
a separately named, reviewed version, not an overwrite.

## Freeze gate

**THE GOLDEN SET MUST BE FINALISED AND COMMITTED BEFORE MODEL BENCHMARKING.**
Commit the final CSV, selection manifest, completed independent sheets,
disagreement report, and agreed protocol/revision history before starting any
model accuracy or performance benchmark. Preserve the source dataset unchanged.
See [the labelling protocol](../docs/labelling_protocol.md) for the fields and
human decisions that must be agreed.

TODO: Decide dataset handling and versioning according to course requirements.
