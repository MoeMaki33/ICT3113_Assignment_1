"""Scaffold for agreement on independent annotator_1 and annotator_2 labels."""
import argparse
from pathlib import Path


def calculate_agreement(golden_set: Path) -> dict:
    # TODO: Read both independent columns and validate against CATEGORIES.
    # TODO: Decide statistic (e.g. Cohen's kappa), missing-label handling,
    # and degenerate cases before implementation. Do not use final_label here.
    raise NotImplementedError("Team must define the agreement protocol")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("golden_set", type=Path)
    args = parser.parse_args()
    parser.exit(2, "TODO: agreement calculation is not implemented; no results generated.\n")
