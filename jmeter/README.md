# JMeter plan scaffold

TODO: Create the plan after the team completes and commits its prediction record.

The eventual plan must read narratives from CSV and send JSON to `POST /tickets`.
Tickets must enter the service through this endpoint only. Escape CSV narratives
correctly when constructing JSON request bodies.

Use **OPEN-LOOP traffic**, with Open Model Thread Group or Precise Throughput
Timer. Configure enough worker capacity to maintain the intended arrival rate;
report any achieved-rate shortfall. Test multiple arrival rates, with values and
durations to be decided by the team. Run every configuration **THREE times**.

Retain every raw `.jtl` CSV under `results/load/` or `results/stress/`, and retain
the corresponding service logs. Save the response `X-Request-ID` in JMeter sample
variables for reconciliation. Record model identity, configuration, run identifier,
timestamps, and errors. Avoid storing full narratives in service logs.

Report p50, p95, and p99 latency, achieved throughput, and error rate. Document
units, percentile calculation, sample selection, and observation window.
At least one stress test must identify a meaningful system limit; define the
limit and stopping criteria before running it.

`scripts/process_jmeter_results.py` accepts a `.jtl` path but is deliberately a
TODO scaffold. No plan has been run and no measurements have been generated.
