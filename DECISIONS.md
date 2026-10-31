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
