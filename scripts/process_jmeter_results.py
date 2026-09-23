"""Scaffold for processing one real JMeter .jtl CSV file."""
import argparse
from pathlib import Path


def process_results(jtl_file: Path) -> dict:
    # TODO: Validate CSV fields timeStamp, elapsed, success; define sample scope.
    # TODO: Count total, successful, and failed requests; error rate = failed / total.
    # TODO: Calculate p50/p95/p99 of elapsed milliseconds using a documented method.
    # TODO: Throughput = count / observation seconds, spanning earliest start
    # through latest completion. Document units, empty files, and zero duration.
    # TODO: Return metrics and source provenance; retain the original .jtl unchanged.
    raise NotImplementedError("JMeter result processing is reserved for Person 4")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jtl_file", type=Path, help="Real JMeter .jtl CSV result file")
    args = parser.parse_args()
    parser.exit(2, "TODO: JMeter result processing is not implemented; no metrics generated.\n")
