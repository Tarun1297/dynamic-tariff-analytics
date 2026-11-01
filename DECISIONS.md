# Decisions

What I chose at each step, why, and what goes wrong without it.

## Phase 1: two dbt targets, dev and ci

- Decision: `dev` builds into `data/warehouse.duckdb` and `ci` builds in
  memory.
- Why: CI has no warehouse file and no API key, but it still has to show that
  every model and test runs. The in-memory database starts empty on each run
  and is built from small sample files.
- Without it: CI cannot run dbt. Then I find broken SQL only on my laptop,
  after the merge.

## Phase 1: profiles.yml in the repo

- Decision: `dbt/profiles.yml` is committed instead of living in `~/.dbt/`.
- Why: DuckDB needs file paths and no passwords. Because of this, a reviewer
  can clone the repo and run it without any setup.
- Without it: every person has to write their own profile before the first
  run.
- Limit: a BigQuery target needs credentials. If I add one, the credentials
  come from environment variables through `env_var()` and never go in the
  file.

## Phase 1: secrets in .env, template in .env.example

- Decision: the API key is only in `.env`, which Git ignores. `.env.example`
  lists the same variable names with empty values.
- Why: the code reads the variable by name at run time. As a result, the key
  never enters Git, and a reviewer can see which variables to set.
- Without it: a key in the code becomes public when I push it. Rolling back
  does not remove it from the history, so I must revoke the key and get a new
  one.

## Phase 1: stay on dbt Core v1

- Decision: I keep dbt Core 1.12, although dbt reports that v2 is available.
- Why: dbt-duckdb and dbt-metricflow are built for v1, and most teams still
  run v1.
- Without it: I spend time on adapter and MetricFlow support instead of on
  models. I will look at v2 again after Phase 11.

## Phase 1: one branch and one pull request per phase

- Decision: each phase gets one branch and one pull request, made of small
  commits.
- Why: I can undo a small commit on its own, and the history shows which step
  broke something. A finished phase is something a reviewer can read and test
  as a whole.
- Without it: I can only undo one big commit all at once. A pull request per
  file costs a review for pieces that do not work alone. `main` only receives
  complete phases that work.

## Phase 2: a half-open interval for each month

- Decision: the pipeline keeps a price only if `start <= t < end`, where
  `start` and `end` are the first days of two months in German time.
- Why: the ENTSO-E client also returns the price at `end`, which is 00:00 on
  the first day of the next month. With the filter, each month loads exactly
  its own rows, and two months never share a row.
- Without it: each month brings one row of the next month. With append,
  that gives 20 duplicate rows. With merge, the last month still adds
  2026-10-01 00:00, which is outside the period.

## Phase 2: the dlt state and the merge as two guards

- Decision: the dlt state lists the loaded months, and the table uses merge on
  `interval_start_utc`.
- Why: the state makes a rerun cheap, because it skips loaded months and makes
  no API calls. The merge makes a rerun safe, because it replaces a row with
  the same timestamp instead of adding it again.
- Without the state: every run downloads all 21 months again. The table stays
  correct, but the run is slow and uses the API quota.
- Without the merge: if a month loads again, for example after I reset the
  state, every row of that month is in the table twice.

## Phase 2: raw keeps UTC and EUR per MWh

- Decision: `raw.day_ahead_prices` stores the timestamp in UTC and the price
  in EUR per MWh, as ENTSO-E sends them.
- Why: raw is an exact copy of the source, and staging does the conversions.
  If a conversion has a bug, I fix staging and rebuild from raw without new
  API calls. UTC also has no clock change, so every timestamp is unique.
- Without it: on 26 October 2025, the hour from 02:00 to 03:00 German time
  happened twice. In German time, those two hours have the same timestamps.

## Phase 3: tariff assumptions

These four values are my own assumptions. Each row of `tariffs.csv` holds the
same reason, so a reviewer sees it next to the number.

- Fixed tariff, 32.0 ct/kWh gross: the middle of the cheapest new-customer
  offers in Hamburg in October 2026. Comparison sites list them at about 27
  to 35 ct/kWh. The price includes energy, grid fee, levies and VAT.
- Fixed tariff, 12.00 EUR per month gross: the typical base fee of those
  offers. It includes the grid base fee and the meter.
- Dynamic tariff, markup of 2.0 ct/kWh gross on the day-ahead price: dynamic
  offers add between 0 and 2.5 ct/kWh. I chose a value in the upper half, so
  the result does not depend on the cheapest offer on the market.
- Dynamic tariff, 6.00 EUR per month gross: dynamic offers charge about 4.50
  to 9 EUR per month. The grid base fee of 72 EUR per year net comes on top.

- Why one fixed price for the whole period: fixed contracts usually guarantee
  the price for 12 to 24 months. I only have prices from October 2026.
- Limit: in early 2025 the grid fee was higher, so a fixed contract signed then
  probably cost more than 32.0 ct/kWh. The comparison therefore slightly
  favours the fixed tariff. If the dynamic tariff still saves money, the
  result holds.
- Limit: a dynamic tariff needs a smart meter. Its fee is not in the model yet.
- Limit: the values come from comparison sites, not from signed contracts.
  The sites differ by several ct/kWh and change their lists daily.
- Limit: the base fees are close. The fixed tariff charges 12.00 EUR per
  month. The dynamic tariff charges 6.00 EUR plus the grid base fee of 7.14 EUR
  gross, which is 13.14 EUR per month. So the energy price decides the result.
- Limit: the markup and the dynamic base fee are typical values, not one
  provider's terms. A real provider can be cheaper or more expensive.
- Limit: the provider names stay out of the repo, as the project rules require.
- Unit: the tariffs are gross because customers see gross prices. The other
  seeds are net, so the models divide the tariff values by 1.19 before they
  add them to net components.
