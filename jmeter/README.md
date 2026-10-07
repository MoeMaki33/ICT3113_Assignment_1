# JMeter plan

`ticket_load_test.jmx` is the single open-loop plan for the load test, the mixed (tickets +
searches) peak-hour test, and every stress-test step. It needs **Apache JMeter 5.6.3** (Open Model
Thread Group). The full procedure, configuration table and metric definitions are in
[`docs/test_playbook.md`](../docs/test_playbook.md).

- **Open loop:** two Open Model Thread Groups with `random_arrivals` (Poisson) at a rate given in
  tickets/searches per hour. A slow service does not slow the arrivals down. There is no
  closed-loop Thread Group.
- **Data:** `data/team_narratives.tsv` holds the team's 1,000 rows (7000–7999) with each narrative
  already JSON-encoded, so quotes, commas and line breaks are escaped correctly in the body
  `{"narrative": ${narrative_json}}`. Regenerate with `python -m scripts.prepare_jmeter_data`.
  Tickets enter the service only through `POST /tickets`; the CSV is never imported.
- **Configurable:** rate, duration, drain, target host/port, search schedule, seed and timeouts are
  `-J` properties. `scripts/run_load_test.py` sets them and writes results to
  `results/<load|stress>/<model-dir>/rate-<X>[_search-<Y>]/run-<N>.jtl` (never overwritten).
- **Evidence:** `results.properties` fixes the `.jtl` CSV format and adds the service's
  `X-Request-ID` (`request_id` column) for reconciliation with `logs/service.log`
  (`scripts/reconcile_logs.py`).

Run through the wrapper:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_load_test --model qwen2.5:7b --rate 250 --search-rate 450 --host <service-ip>
```

Equivalent raw command (the wrapper also records it in each run's `.json`):

```text
jmeter -n -t jmeter/ticket_load_test.jmx -q jmeter/results.properties -l run-1.jtl -j run-1.jmeter.log
  -Jhost=<service-ip> -Jport=8000 -Jprotocol=http -Jrate=250 -Jduration_s=720 -Jdrain_s=190
  -Jsearch_schedule=rate(450/hour)random_arrivals(720s)pause(190s) -Jseed=311301 -Jsearch_seed=311351
  -Jdata_file=<abs>/jmeter/data/team_narratives.tsv -Jsearch_file=<abs>/jmeter/data/search_terms.txt -Jtimeout_ms=180000
```

Never pass a search rate of 0 inside a `rate(...)` schedule: JMeter 5.6.3 then waits forever after
the test. The wrapper uses `pause(1s)` when searches are off.
