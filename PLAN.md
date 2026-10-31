# dynamic-tariff-analytics: build plan

## Goal

Question: did a normal German household save money on a dynamic tariff
compared with a fixed tariff, month by month, and what does that mean for a
provider's revenue and active contracts?

Version 1 uses a normal household only, with no EV or heat pump. Version 2,
optional, adds one EV as a shiftable load.

Stack: dlt for loading, dbt on DuckDB (BigQuery optional), MetricFlow,
Metabase, and Claude Code as the way the project is built.

The provider is described as "a dynamic tariff provider". All tariff values
are my own assumptions, set in seed files with a reason for each.

## Data

Prices, load profiles and grid fees are real. Customers and contracts are
synthetic, because no company publishes its CRM. The synthetic part is
labelled clearly in the README.

| Data | Real or synthetic | Grain | How we get it | Lands in |
|---|---|---|---|---|
| Day-ahead prices, DE-LU zone | Real | 15 min since Oct 2025, hourly before | ENTSO-E API, loaded by dlt | `raw.day_ahead_prices` |
| Household load profile H25 | Real (BDEW, 2025 profiles) | 15 min, per month and day type | Download the 2025 profile file from BDEW once, save as CSV | seed `bdew_load_profiles` |
| Grid fee, incl. §14a Module 3 time windows | Real, one grid operator | Price per kWh per time window, per year | Copy from the operator's published price sheet | seed `grid_fees` |
| Taxes and levies (electricity tax, VAT, others) | Real | Price per kWh, with valid-from date | Copy from official sources, with the link in the seed | seed `tariff_components` |
| Tariff assumptions: fixed price, markup, base fee | My assumptions | Per tariff, with valid-from date | Set by me, with a reason for each value | seed `tariffs` |
| Customers, contracts, tariff switches, cancellations | Synthetic | One row per customer and per contract event | A Python script with a fixed random seed, about 1,000 customers | `raw.crm_*` |

Why synthetic CRM data is fine: the point is to show modelling of a contract
business (active contracts, churn, tariff switches). The script is in the
repo, so anyone can re-create the same data.

Why not one meter row per customer per quarter-hour: 1,000 customers × 35,040
quarter-hours is 35 million rows a year, and they would all be the same
profile scaled up. Instead, cost is computed once per profile and
quarter-hour, then scaled by each customer's yearly consumption.

## Structure

Five layers, each with one job: sources, staging, intermediate, marts,
semantic and serve. Data only flows down. Dashboards and metrics read only
the two fact tables and their dimensions.

The grain of every table is written in its YAML description.

| Model | Grain (one row per) | Key tests |
|---|---|---|
| `stg_entsoe__prices` | price interval (15 min or 1 h) | unique + not_null on start time |
| `int_quarter_hour_prices` | tariff × quarter-hour | price components add up to the total |
| `int_profile_cost_monthly` | tariff × month | cost per kWh > 0 |
| `int_contract_periods` | contract × tariff period | periods never overlap per customer |
| `int_contract_months` | contract × month active | no month after cancellation |
| `fct_invoice_monthly` | customer × month | unique combination; total = sum of parts; relationships to dims |
| `fct_contract_events` | contract event | event type in (signup, switch, cancel) |
| `dim_customer` | customer | unique + not_null |
| `dim_tariff` | tariff × valid-from date | no overlapping validity |
| `dim_month` | month | unique |

Folders: `pipelines/` (dlt), `scripts/` (CRM generator),
`dbt/models/staging`, `intermediate`, `marts`, `semantic`, `dbt/seeds`,
`dbt/tests`.

## Build plan

One phase = one branch, one pull request, one merge. Phases 0 to 5 fit one
weekend, phases 6 to 9 a second, and 10 to 11 a few evenings. Times are rough
estimates.

### Phase 0: Git refresher (1 evening)

- Why: Git basics are a must-have for the role, and every phase ships as a
  pull request.
- Steps: branch, commit, push, pull request, review, merge, pull. Practise on
  a throwaway repo.
- Done when: one branch-to-merge cycle without help.

### Phase 1: Repo and tools (2 h)

- Why: a clean skeleton with rules means every later step has a place to go.
- Steps: create the repo, `pyproject.toml`, `.gitignore` (`.env`, `data/`),
  `CLAUDE.md` with learning mode, `PLAN.md`, `dbt init`, and `profiles.yml`
  with two targets: `dev` writes `data/warehouse.duckdb`, `ci` runs in memory
  on small sample files.
- Done when: `dbt debug` passes for both targets.

### Phase 2: Load prices with dlt (3 h)

- Why: dlt is the loading tool in the target stack. Loading raw data is kept
  apart from transforming it, so a broken source never breaks the models
  silently.
- Steps: a dlt pipeline with one resource that calls ENTSO-E for the DE-LU
  zone month by month, from January 2025 to September 2026, into the raw
  schema of DuckDB. Months already loaded are skipped.
- Done when: every day has 24 rows before 1 October 2025 and 96 after (92 or
  100 on DST days), checked with a query I write.

### Phase 3: Reference data as seeds (2 h)

- Why: data that changes rarely and must be reviewed (profiles, fees, taxes,
  tariff assumptions) belongs in version control, with a source and a
  valid-from date on every row.
- Steps: seeds `bdew_load_profiles`, `grid_fees`, `tariff_components`,
  `tariffs`.
- Done when: `dbt seed` loads them, and tests check no empty prices and no
  overlapping validity periods.

### Phase 4: Synthetic CRM (3 h)

- Why: a contract business needs customers, contracts and cancellations to
  model. A fixed random seed makes the data the same on every run.
- Steps: `scripts/generate_crm.py` writes about 1,000 customers (id, signup
  date, yearly kWh) and contract events (signup, tariff switch, cancellation,
  each with a date and a tariff).
- Done when: two runs give identical files, and the counts match my
  prediction.

### Phase 5: Staging (3 h)

- Why: one place to clean each source: rename, cast types, convert UTC to
  German time, fix units. No business logic.
- Steps: one staging model per source and seed.
- Done when: `dbt build -s staging` passes, with unique and not_null on every
  key.

### Phase 6: Contract history (2 h)

- Why: a customer can switch tariff, so "which tariff on which day" needs a
  history table with valid-from and valid-to dates (a type 2 slowly changing
  dimension).
- Steps: `int_contract_periods` built from the event log with `LEAD()`. Write
  in `DECISIONS.md` why a dbt snapshot is the tool when a source overwrites
  rows instead of logging events.
- Done when: periods never overlap per customer (a test), and a switched
  customer shows two periods.

### Phase 7: Cost per quarter-hour and active months (4 h)

- Why: this is the business logic. Cost is computed once per profile per
  quarter-hour, not per customer, which keeps the model small.
- Steps: `int_quarter_hour_prices` (day-ahead price + markup + grid fee +
  taxes, per tariff), `int_profile_cost_monthly` (EUR per kWh per month,
  dynamic and fixed), `int_contract_months` (one row per contract per month
  it was active, from a month spine).
- Done when: one test day calculated by hand in Excel matches the model to
  the cent.

### Phase 8: Marts (3 h)

- Why: facts with a clear grain are what dashboards and metrics read. A wrong
  grain double-counts revenue.
- Steps: `dim_customer`, `dim_tariff`, `dim_month`, `fct_invoice_monthly`
  (customer × month: kWh, energy, grid fee, taxes, base fee, total, and what
  the fixed tariff would have cost), `fct_contract_events` (one row per
  event).
- Done when: grain tests pass, and invoice total = sum of its parts (a test).

### Phase 9: Semantic layer (3 h)

- Why: a metric defined once gives the same number everywhere.
- Steps: MetricFlow semantic models and metrics: active contracts, new
  contracts, cancellations, churn rate, revenue, average saving vs fixed.
- Done when: `mf query --metrics active_contracts --group-by
  metric_time__month` matches my own SQL count.

### Phase 10: Metabase (half a day)

- Why: dashboards should read only certified models, never raw tables.
- Steps: two dashboards: Product (saving vs fixed by month) and Marketing
  (signups, cancellations, churn).
- Done when: every question uses a mart model; screenshots in the README.

### Phase 11: CI, docs and README (3 h)

- Why: tests and docs are part of "done", and the README is what a reviewer
  reads first.
- Steps: GitHub Actions runs ruff, sqlfluff and `dbt build --target ci`.
  README: question, answer, one chart, how to run, lineage, the
  synthetic-data note, limits.
- Done when: CI is green on the merged pull request.

### Phase 12, optional: EV as a shiftable load (4 h)

- Why: it shows the core idea of a dynamic tariff, moving load to cheap
  hours, in one SQL model.
- Steps: a seed with EV assumptions (energy per night, wallbox power, plug-in
  and leave times). `int_ev_charging` ranks each night's quarter-hours by
  price with `RANK()`, then charges in the cheapest ones until the need is
  met (a running `SUM()`). Compare with charging right after plug-in.
- Done when: one night checked by hand matches the model.

### Phase 13, optional: Dagster and BigQuery

One Dagster job that runs the dlt load, then `dbt build`. A `bigquery` target
on the free sandbox.

## Assumptions and open questions

Set in seed files, each with a one-line reason. A reviewer will challenge the
numbers, so the reason matters more than the value.

| Item | What to decide | Where |
|---|---|---|
| Grid operator | One operator and its §14a Module 3 price sheet, for example Hamburg's. Not found yet. | seed `grid_fees` |
| Fixed tariff price | A typical German fixed price per kWh and base fee, from a public comparison | seed `tariffs` |
| Dynamic tariff | Markup per kWh and monthly base fee: my own assumptions | seed `tariffs` |
| Taxes and levies | Current values with valid-from dates and the official link | seed `tariff_components` |
| Customer yearly use | A range around a typical household, for example 2,000 to 4,000 kWh | `generate_crm.py` |
| Churn | Monthly cancellation probability for the synthetic customers | `generate_crm.py` |
| Period | January 2025 to September 2026, so the 15-minute switch on 1 October 2025 is inside | dlt pipeline |
| EV (v2 only) | Energy per night, wallbox power, plug-in and leave times | seed `ev_assumptions` |

Limits to state in the README: the household follows the standard profile
exactly, there are no real smart-meter readings, the CRM is synthetic, and the
EV model assumes perfect knowledge of next-day prices (which holds for
day-ahead, since prices are published the day before).

## Sources

- Bundesnetzagentur: §14a EnWG grid fee modules (Module 3 offered from April
  2025, three price levels)
- standardlastprofile package docs: BDEW 2025 profiles H25, P25, S25,
  15-minute values
- MotherDuck: dbt MetricFlow with DuckDB
- MotherDuck: Metabase DuckDB driver
- Google Cloud: BigQuery sandbox
