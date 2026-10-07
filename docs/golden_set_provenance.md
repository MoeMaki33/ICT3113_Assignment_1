# Golden-set source provenance review

Team **7**, seed **3113**, count **180**. No selected row, narrative, human
annotation, adjudication or final golden label was changed in this correction.
Frozen numerical predictions were not edited.

## Raw-source discrepancy

The original selection-time `source_sha256` remains in `selection.json`:

```text
20e8ed8aeec33617a329c2785020b9a846ff33596ee5430883511ee87ca00d8c
```

The canonical `data/team.csv` raw-byte SHA-256 is:

```text
3174ac682d4796ab44a32e809822c3d313cdd21429707def5aaed8b55ff1a99c
```

`git log -- data/team.csv` identifies one source-file history commit:
`47f6f7b34efb0030db90dc1822129a9c9e460638`
(Add golden test set labelling workflow and agreement tooling). Its raw Git
blob is byte-for-byte identical to the current canonical file. No source blob
matching the original recorded hash was found in that available file history.
The cause of the discrepancy is unknown. The historical hash is retained as
evidence, rather than replaced or described as a verified canonical hash.

## Reproduction and integrity

The whole-source hash is provenance metadata; it is not an input to ticket
ranking. `create_golden_set.select_rows` ranks the UTF-8 JSON encoding of
`[seed, original row number, narrative]` using SHA-256, then sorts the chosen
rows by original row number.

The canonical source reproduces all 180 stored original row IDs using the
unchanged count and seed. The frozen golden-set row/narrative pairs match that
selection. All 1,000 assigned Team 7 rows/narratives are independently checked
against `data/ict3113_tickets.csv`. Human annotation hashes and agreement
metrics match the stored evidence, and final labels reproduce from the human
agreement and disagreement/adjudication records: 153 agreements, 27
disagreements, 85.0% agreement, Cohen's kappa 0.8239066632849016.

## Validation policy

`selection.json.source_provenance_review` records both hashes, the inspected
commit, the unavailable-original-source finding, a digest of the unchanged
selection identity, and raw SHA-256 digests of the course source, frozen golden
set, both annotator sheets, disagreement report and agreement evidence.

The validator checks these pins and this document whenever the review exists,
even if the two source hashes later match. Undocumented mismatches, missing or
inconsistent review metadata, changed canonical bytes or evidence, and failed
deterministic/content/annotation checks remain fatal. A reviewed mismatch is
reported as a provenance warning only after all checks pass. This distinguishes
the investigated raw-byte provenance gap from a selection or label integrity
failure; it does not establish that the unavailable original bytes were correct.

This is a separate provenance correction after the local pre-benchmark freeze.
It does not amend the freeze, regenerate the golden set, use smoke-test results,
or claim a new human approval.
