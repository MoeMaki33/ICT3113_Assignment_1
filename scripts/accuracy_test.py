"""Future evaluation client. No evaluation is executed by this scaffold."""
import argparse
from pathlib import Path


def evaluate(golden_set: Path, api_url: str, output: Path) -> None:
    # TODO: Confirm frozen golden set and prediction record are committed.
    # TODO: Read CSV; validate nonempty narratives and seven-category final_label.
    # TODO: POST each narrative synchronously to api_url + '/tickets' using httpx.
    # TODO: Retain returned category, ticket id, X-Request-ID, and request errors.
    # TODO: Compare category with final_label; define handling of failed requests.
    # TODO: Calculate overall accuracy and per-category accuracy (recall).
    # TODO: Generate confusion matrix in central CATEGORIES order, including zeros.
    # TODO: Save raw predictions and derived metrics under output, without overwrite.
    raise NotImplementedError("Accuracy evaluation requires the team's frozen protocol")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("golden_set", type=Path)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--output", type=Path, default=Path("results/accuracy"))
    args = parser.parse_args()
    parser.exit(2, "TODO: accuracy evaluation is not implemented; no requests sent.\n")
