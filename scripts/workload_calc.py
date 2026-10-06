"""Workload model calculations: average, peak, design and test arrival rates, and search rate.

Every input is labelled SOURCE (a published figure, cited in docs/workload_model.md) or
ESTIMATE (a team assumption, derivation in docs/workload_model.md). Change an input here and
re-run; nothing else needs editing. No measured result is used.

    python scripts/workload_calc.py --json results/workload/workload_calc.json
"""
import argparse
import json
import math
from datetime import date
from pathlib import Path

INPUTS = {
    "fca_banking_credit_card_complaints_2024_h2": {
        "value": 839_526, "kind": "SOURCE",
        "note": "Complaints received by UK firms, banking and credit cards product group, 1 Jul-31 Dec 2024 (FCA)",
    },
    "period_start": {"value": "2024-07-01", "kind": "SOURCE", "note": "FCA 2024 H2 reporting period"},
    "period_end": {"value": "2024-12-31", "kind": "SOURCE", "note": "FCA 2024 H2 reporting period"},
    "client_market_share": {"value": 0.25, "kind": "ESTIMATE", "note": "Client is one top-tier retail bank"},
    "weekend_day_factor": {"value": 0.5, "kind": "ESTIMATE", "note": "A weekend day receives half a weekday's tickets"},
    "daytime_share": {"value": 0.80, "kind": "ESTIMATE", "note": "Share of a weekday's tickets arriving 08:00-20:00"},
    "daytime_hours": {"value": 12, "kind": "ESTIMATE", "note": "08:00-20:00"},
    "peak_hour_factor": {"value": 2.0, "kind": "ESTIMATE", "note": "Busiest hour (Monday morning) vs average daytime hour"},
    "growth_headroom": {"value": 1.25, "kind": "ESTIMATE", "note": "Margin for growth and bursts above the estimated peak"},
    "design_rate_step": {"value": 50, "kind": "ESTIMATE", "note": "Design peak rounded up to a multiple of this (tickets/h)"},
    "tickets_per_agent_day": {"value": 30, "kind": "ESTIMATE", "note": "Tickets one agent handles per weekday"},
    "searches_per_agent_hour": {"value": 10, "kind": "ESTIMATE", "note": "GET /search calls per agent per working hour"},
    "test_rate_multipliers": {"value": [0.5, 1.0, 2.0], "kind": "ESTIMATE", "note": "Below, at and above the design peak"},
    "measurement_window_minutes": {"value": 10, "kind": "ESTIMATE",
                                   "note": "Suggested steady-state window per run (Person 5 decides)"},
}


def value(name: str):
    return INPUTS[name]["value"]


def count_days(start: date, end: date) -> tuple[int, int]:
    """Return (weekdays, weekend days) from start to end inclusive."""
    weekdays = weekend = 0
    for ordinal in range(start.toordinal(), end.toordinal() + 1):
        if date.fromordinal(ordinal).weekday() < 5:
            weekdays += 1
        else:
            weekend += 1
    return weekdays, weekend


def calculate() -> dict:
    start, end = date.fromisoformat(value("period_start")), date.fromisoformat(value("period_end"))
    weekdays, weekend_days = count_days(start, end)
    client_period = value("fca_banking_credit_card_complaints_2024_h2") * value("client_market_share")
    weighted_days = weekdays + value("weekend_day_factor") * weekend_days
    weekday_daily = client_period / weighted_days
    daytime_hourly = weekday_daily * value("daytime_share") / value("daytime_hours")
    night_hourly = weekday_daily * (1 - value("daytime_share")) / (24 - value("daytime_hours"))
    peak_hourly = daytime_hourly * value("peak_hour_factor")
    step = value("design_rate_step")
    design_peak = math.ceil(peak_hourly * value("growth_headroom") / step) * step
    agents = math.ceil(weekday_daily / value("tickets_per_agent_day"))
    peak_searches = agents * value("searches_per_agent_hour")
    window = value("measurement_window_minutes")

    def rate(per_hour: float, formula: str) -> dict:
        return {"per_hour": round(per_hour, 1), "per_second": round(per_hour / 3600, 4),
                "mean_interarrival_s": round(3600 / per_hour, 1), "formula": formula}

    test_rates = []
    for multiplier in value("test_rate_multipliers"):
        per_hour = design_peak * multiplier
        samples = per_hour * window / 60
        test_rates.append({
            "label": f"{multiplier:g}x design peak",
            **rate(per_hour, f"design_peak x {multiplier:g}"),
            "expected_samples_per_window": round(samples, 1),
            "expected_samples_three_runs": round(3 * samples, 1),
        })

    return {
        "period_days": {"weekdays": weekdays, "weekend_days": weekend_days,
                        "calendar_days": weekdays + weekend_days},
        "client_tickets_per_period": {"value": round(client_period, 1),
                                      "formula": "fca_banking_credit_card_complaints_2024_h2 x client_market_share"},
        "client_tickets_per_month": {"value": round(client_period / 6, 1), "formula": "client_tickets_per_period / 6"},
        "weighted_days": {"value": weighted_days, "formula": "weekdays + weekend_day_factor x weekend_days"},
        "weekday_tickets_per_day": {"value": round(weekday_daily, 1),
                                    "formula": "client_tickets_per_period / weighted_days"},
        "weekend_tickets_per_day": {"value": round(weekday_daily * value("weekend_day_factor"), 1),
                                    "formula": "weekday_tickets_per_day x weekend_day_factor"},
        "average_daytime_rate": rate(daytime_hourly, "weekday_tickets_per_day x daytime_share / daytime_hours"),
        "non_peak_night_rate": rate(night_hourly,
                                    "weekday_tickets_per_day x (1 - daytime_share) / (24 - daytime_hours)"),
        "estimated_peak_rate": rate(peak_hourly, "average_daytime_rate x peak_hour_factor"),
        "design_peak_rate": rate(design_peak,
                                 "ceil(estimated_peak_rate x growth_headroom / design_rate_step) x design_rate_step"),
        "test_arrival_rates": test_rates,
        "agents_on_duty": {"value": agents, "formula": "ceil(weekday_tickets_per_day / tickets_per_agent_day)"},
        "peak_search_rate": rate(peak_searches, "agents_on_duty x searches_per_agent_hour"),
        "max_mean_service_time_at_design_peak_s": {
            "value": round(3600 / design_peak, 1),
            "formula": "3600 / design_peak_rate; with one request processed at a time, a mean "
                       "classification time above this means the queue grows without bound",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="Also write inputs and results to this file")
    args = parser.parse_args()
    record = {"inputs": INPUTS, "results": calculate()}
    text = json.dumps(record, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
