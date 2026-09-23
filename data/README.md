# Dataset workspace

No tickets are seeded. A fresh deployment creates an empty SQLite database;
subsequent restarts retain tickets. All service submissions use `POST /tickets`.

Obtain the course CSV and actual team number from the course/team. Confirm the
row indexing convention: the extraction helper uses zero-based data rows,
excluding the header, and selects `team_number * 1000` through
`team_number * 1000 + 999`, inclusive. Pass the exact narrative column name.

```powershell
python scripts/extract_team_data.py data/course.csv data/team.csv --team-number <TEAM_NUMBER> --narrative-column "<COLUMN_NAME>"
python scripts/create_golden_set.py data/team.csv data/golden_draft.csv
```

Both helpers refuse to overwrite existing output. The annotation template has
`row,narrative,annotator_1,annotator_2,final_label,notes`; all label fields start
blank. Original source labels are not copied as ground truth. Arrange independent
labelling, adjudication, and freezing according to the team's protocol.

TODO: Decide dataset handling and versioning according to course requirements.
