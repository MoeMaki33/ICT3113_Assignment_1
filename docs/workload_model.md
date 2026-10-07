# Workload model

Owner: Person 4. Status: **FINAL (2026-10-07)**: the team reviews it before the freeze commit.
Every figure is either **source-derived** (section 2, with source, URL, date and exact figure)
or **our estimate** (section 3, with how it was derived). No figure here is a measurement of
our system.

Reproduce the numbers:

```powershell
python scripts/workload_calc.py --json results/workload/workload_calc.json
python scripts/ticket_lengths.py data/team.csv --subset data/golden_set_final.csv --json results/workload/ticket_lengths.json
```

## 1. Client scenario

The client is a **top-tier retail bank** whose customer-relations desk receives complaint
tickets about banking and credit-card products. Customers submit complaints online at any
time; each ticket is classified on arrival by `POST /tickets` and routed to a team of human
agents, who also look up earlier tickets with `GET /search`.

## 2. Source-derived figures

| # | Source | URL | Published | Exact figure | How we use it |
|---|---|---|---|---|---|
| S1 | FCA, *Aggregate complaints data 2024 H2* | https://www.fca.org.uk/data/complaints-data/aggregate-complaints-data-2024-h2 | 29 Apr 2025 | Banking and credit cards: **839,526** complaints received by firms, 1 Jul–31 Dec 2024 (2024 H1: 850,983). All products: 1.78m. | Base volume. FCA data counts complaints that firms receive **directly**, which is what a firm's own complaints desk handles. Figure and publication date confirmed manually on the FCA page by Person 4 (2026-10-07). |
| S2 | CFPB, *Consumer Response Annual Report, January 1 – December 31, 2024* | https://www.consumerfinance.gov/data-research/research-reports/2024-consumer-response-annual-report/ (PDF: https://files.consumerfinance.gov/f/documents/cfpb_cr-annual-report_2025-05.pdf) | 1 May 2025 | "In 2024, the CFPB received approximately **3,187,900** complaints." "Consumers submitted **98%** of complaints by visiting the CFPB's website and 0.9% by calling." "Complaints about credit and consumer reporting accounted for **85%** of complaints received. Most of these complaints were submitted about the nationwide consumer reporting agencies." | (a) The 98% online share supports modelling arrivals around the clock rather than only in desk hours. (b) Because 85% of CFPB complaints concern the three credit bureaus, CFPB totals do not describe a bank's desk, so we do not take the client's volume from them. Verified against the report PDF. |
| S3 | Course dataset, our team's rows | `data/team.csv` (rows 7000–7999 of `data/ict3113_tickets.csv`) | Released on xSiTe, Week 1 | Narrative length distribution, section 5. Every narrative in the 50,000-row course extract is **200–2,000 characters**. | Ticket-length distribution for test traffic and latency predictions. Output: `results/workload/ticket_lengths.json`. |
| S4 | Our golden-set annotation | `results/accuracy/agreement.json` | 2026-10-06 | Two annotators agreed on **153/180 = 85.0%** of tickets (Cohen's κ = 0.824). | Anchor for the accuracy requirement (`docs/requirements.md`). |

## 3. Our estimates and assumptions

| # | Estimate | Value | How it was derived |
|---|---|---|---|
| E1 | Client share of UK banking and credit-card complaints | **25%** | The client is one of the few largest UK retail banks. Large banking groups account for a large share of retail accounts. 25% is our judgement of one top-tier group's share; no per-firm figure was used. This is the most influential estimate. |
| E2 | Weekend day volume | **0.5×** a weekday | Online submission continues at weekends (S2), but fewer customers deal with their finances then. Judgement. |
| E3 | Daytime share | **80%** of a weekday's tickets arrive 08:00–20:00 | Most online activity happens in waking hours; 20% covers evenings and night. Judgement. |
| E4 | Peak-hour factor | Busiest hour = **2.0×** the average daytime hour (Monday morning) | Issues accumulated over the weekend are raised at the start of the week. Judgement. |
| E5 | Growth headroom | **1.25×** the estimated peak, rounded up to a multiple of 50/h | Margin for volume growth and short bursts above the hourly average. |
| E6 | Agent productivity | **30** tickets per agent per weekday | Judgement for investigating and responding to a complaint. Used only to size the search load. |
| E7 | Agent search rate | **10** `GET /search` calls per agent per working hour | An agent looks up related or earlier tickets for most tickets handled. Judgement. |
| E8 | Category mix | Not modelled from the dataset | The course extract is balanced (about 7,143 rows per category), so it does not reflect a real desk's mix. Test traffic uses our team's rows as they are. |

## 4. Derived workload

All values come from `scripts/workload_calc.py` (`results/workload/workload_calc.json`).

| Quantity | Formula | Value |
|---|---|---|
| Client tickets, 2024 H2 | S1 × E1 = 839,526 × 0.25 | 209,882 |
| Client tickets per month | ÷ 6 | ≈ 34,980 |
| Days in 2024 H2 | counted from the calendar | 132 weekdays, 52 weekend days |
| Weighted days | 132 + 0.5 × 52 | 158 |
| Weekday tickets per day | 209,882 / 158 | **≈ 1,328** |
| Weekend tickets per day | 1,328 × 0.5 | ≈ 664 |
| Average daytime rate (non-peak) | 1,328 × 0.80 / 12 h | **≈ 89 tickets/h** (one every 41 s) |
| Night rate (off-peak) | 1,328 × 0.20 / 12 h | ≈ 22 tickets/h |
| Estimated peak rate | 89 × 2.0 | **≈ 177 tickets/h** |
| **Design peak rate** | ⌈177 × 1.25 / 50⌉ × 50 | **250 tickets/h** (0.069/s; one every 14.4 s) |
| Agents on duty | ⌈1,328 / 30⌉ | 45 |
| Peak search rate | 45 × 10 | **450 searches/h** (0.125/s) |
| Highest mean classification time the service can sustain at design peak | 3600 / 250 | 14.4 s per ticket (with one classification at a time) |

### Peak and non-peak periods

| Period | Rate |
|---|---|
| Weekday peak hour (Monday morning), design value | 250 tickets/h, 450 searches/h |
| Weekday daytime, average | ≈ 89 tickets/h |
| Weekday night | ≈ 22 tickets/h |
| Weekend day | about half the weekday rates |

Requirements are set at the **design peak**, so they cover the busiest hour.

### Test arrival rates

| Label | Rate | Mean gap between tickets |
|---|---|---|
| 0.5× design peak | **125 tickets/h** (0.035/s) | 28.8 s |
| 1× design peak | **250 tickets/h** (0.069/s) | 14.4 s |
| 2× design peak | **500 tickets/h** (0.139/s) | 7.2 s |

## 5. Ticket-length distribution (team rows)

From `results/workload/ticket_lengths.json`. Percentiles use the nearest-rank method.
Estimated tokens = characters / 4, a rule of thumb, not a tokenizer count.

| Measure (n = 1,000) | min | mean | median | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| Characters | 200 | 881.5 | 756.5 | 755 | 1,791 | 1,925 | 1,988 |
| Words | 28 | 157.4 | 136 | 136 | 319 | 358 | 389 |
| Estimated tokens | 50 | 220.8 | 189.5 | 189 | 448 | 482 | 497 |

| Characters | 0–249 | 250–499 | 500–999 | 1,000–1,999 | 2,000+ |
|---|---|---|---|---|---|
| Share of tickets | 4.6% | 22.4% | 35.6% | 37.4% | 0% |

The golden-set subset (n = 180) is similar: median 870 characters, p95 1,792, p99 1,968.

**Limitation:** the course extract contains only narratives of 200–2,000 characters. Real
complaints can be longer, and longer inputs take longer to classify, so production latency may
be higher than measured with this traffic.

## 6. Notes for Person 5 (recommendations only)

Person 5 owns run length, warm-up, percentile method and the test matrix. From the rates above:

| Rate | Expected tickets in a 10-minute window | Over three runs |
|---|---|---|
| 125/h | ≈ 21 | ≈ 63 |
| 250/h | ≈ 42 | ≈ 125 |
| 500/h | ≈ 83 | ≈ 250 |

- A p99 from about 42 samples is close to the maximum. Consider reporting p50 and p95 per run (mean and spread) and p99 pooled across the three runs as well.
- Consider excluding a warm-up period, e.g. the first 2 minutes, which also covers model loading.
- The search requirement needs mixed traffic: 450 searches/h alongside 250 tickets/h.
