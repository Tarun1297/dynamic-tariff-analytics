"""Generate SYNTHETIC customers and contract events for a dynamic tariff provider.

The data is made up. No real customer appears here. A fixed random seed makes
every run produce exactly the same files.

Run from the repo root, after the prices are loaded and `dbt seed` has run:
    python scripts/generate_crm.py

Writes data/crm/customers.csv and data/crm/contract_events.csv, and loads them
into raw.crm_customers and raw.crm_contract_events in data/warehouse.duckdb.
"""
import csv
import datetime as dt
import random
from pathlib import Path

import duckdb

SEED = 42
N_CUSTOMERS = 1000
FIRST_DAY = dt.date(2025, 1, 1)
LAST_DAY = dt.date(2026, 9, 30)
KWH_MIN, KWH_MAX = 2000, 4000
SHARE_DYNAMIC = 0.70
P_SWITCH = 0.01  # per active customer and month
P_CANCEL_BASE = 0.01  # per active contract and month
P_CANCEL_PER_CT = 0.0025  # extra per ct/kWh that dynamic cost more than fixed last month

WAREHOUSE = Path("data/warehouse.duckdb")
OUT_DIR = Path("data/crm")

# Rough gross price per kWh of the dynamic tariff minus the fixed tariff, per month.
# The proper calculation is built in dbt (Phase 7). This one only drives churn.
MONTHLY_PRICE_GAP_SQL = """
with days as (
    select cast(d as date) as day
    from range(date '2025-01-01', date '2026-10-01', interval 1 day) as t (d)
),

typed as (
    select
        day,
        extract(doy from day) as n,
        extract(month from day) as m,
        case
            when day in (select holiday_date from main.public_holidays) or dayofweek(day) = 0 then 'FT'
            when dayofweek(day) = 6 or (extract(month from day) = 12 and extract(day from day) in (24, 31)) then 'SA'
            else 'WT'
        end as day_type
    from days
),

quarter_hours as (
    select
        t.day,
        t.day + cast(p.interval_start as time) as ts_local,
        p.kwh_per_1m_kwh_year
        * round(-3.92e-10 * pow(t.n, 4) + 3.2e-7 * pow(t.n, 3) - 7.02e-5 * pow(t.n, 2) + 2.1e-3 * t.n + 1.24, 4)
            as kwh
    from typed as t
    inner join main.bdew_load_profiles as p on p.month = t.m and p.day_type = t.day_type
),

prices as (
    select interval_start_utc at time zone 'Europe/Berlin' as ts_local, price_eur_mwh
    from raw.day_ahead_prices
),

monthly_spot as (
    select
        date_trunc('month', q.day) as month_start,
        sum(q.kwh * p.price_eur_mwh) / sum(q.kwh) / 10 as spot_ct
    from quarter_hours as q
    asof inner join prices as p on q.ts_local >= p.ts_local
    group by 1
),

per_kwh_net as (
    select
        s.month_start,
        s.spot_ct
        + (select value from main.grid_fees as g
            where g.item = 'energy_price' and s.month_start between g.valid_from and g.valid_until)
        + (select sum(value) from main.tariff_components as c
            where c.unit = 'ct_per_kwh'
              and s.month_start >= c.valid_from
              and s.month_start <= coalesce(c.valid_until, date '9999-12-31'))
            as net_ct_without_markup
    from monthly_spot as s
)

select
    strftime(n.month_start, '%Y-%m') as month,
    (n.net_ct_without_markup + markup.value / 1.19) * 1.19 - fixed.value as gap_ct
from per_kwh_net as n
cross join (select value from main.tariffs where tariff = 'dynamic' and item = 'markup') as markup
cross join (select value from main.tariffs where tariff = 'fixed' and item = 'energy_price') as fixed
order by 1
"""


def month_starts():
    m = FIRST_DAY
    while m <= LAST_DAY:
        yield m
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def random_day_in_month(rng, month_start):
    next_month = (month_start.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return month_start + dt.timedelta(days=rng.randrange((next_month - month_start).days))


def simulate(price_gap_by_month, seed=SEED):
    """Return (customers, events) as lists of dicts. Same seed and gaps give the same result."""
    rng = random.Random(seed)
    span_days = (LAST_DAY - FIRST_DAY).days + 1
    signups = sorted(FIRST_DAY + dt.timedelta(days=rng.randrange(span_days)) for _ in range(N_CUSTOMERS))

    customers, events, state = [], [], {}
    for i, signup_date in enumerate(signups, start=1):
        customer_id = f"C{i:04d}"
        tariff = "dynamic" if rng.random() < SHARE_DYNAMIC else "fixed"
        customers.append({
            "customer_id": customer_id,
            "signup_date": signup_date.isoformat(),
            "yearly_kwh": round(rng.uniform(KWH_MIN, KWH_MAX), -1),
            "data_origin": "synthetic",
        })
        events.append({"customer_id": customer_id, "contract_id": f"K{i:04d}",
                       "event_date": signup_date, "event_type": "signup", "tariff": tariff})
        state[customer_id] = {"tariff": tariff, "signup": signup_date, "contract_id": f"K{i:04d}"}

    previous_month = None
    for month_start in month_starts():
        gap = price_gap_by_month.get(previous_month, 0.0) if previous_month else 0.0
        for customer_id, s in state.items():
            # Only customers who signed up before this month and have not cancelled.
            if s["signup"] >= month_start or s.get("cancelled"):
                continue
            p_cancel = P_CANCEL_BASE
            if s["tariff"] == "dynamic":
                p_cancel += P_CANCEL_PER_CT * max(0.0, gap)
            roll = rng.random()
            if roll < p_cancel:
                s["cancelled"] = True
                event_type, tariff = "cancel", s["tariff"]
            elif roll < p_cancel + P_SWITCH:
                s["tariff"] = "fixed" if s["tariff"] == "dynamic" else "dynamic"
                event_type, tariff = "switch", s["tariff"]
            else:
                continue
            events.append({"customer_id": customer_id, "contract_id": s["contract_id"],
                           "event_date": random_day_in_month(rng, month_start),
                           "event_type": event_type, "tariff": tariff})
        previous_month = month_start.strftime("%Y-%m")

    events.sort(key=lambda e: (e["event_date"], e["customer_id"]))
    for n, e in enumerate(events, start=1):
        e["event_id"] = f"E{n:05d}"
        e["event_date"] = e["event_date"].isoformat()
        e["data_origin"] = "synthetic"
    return customers, events


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    con = duckdb.connect(str(WAREHOUSE))
    price_gap_by_month = dict(con.sql(MONTHLY_PRICE_GAP_SQL).fetchall())
    customers, events = simulate(price_gap_by_month)

    customers_csv = OUT_DIR / "customers.csv"
    events_csv = OUT_DIR / "contract_events.csv"
    write_csv(customers_csv, customers, ["customer_id", "signup_date", "yearly_kwh", "data_origin"])
    write_csv(events_csv, events,
              ["event_id", "customer_id", "contract_id", "event_date", "event_type", "tariff", "data_origin"])

    con.sql("create schema if not exists raw")
    con.sql(f"create or replace table raw.crm_customers as select * from read_csv('{customers_csv.as_posix()}')")
    con.sql(f"create or replace table raw.crm_contract_events as select * from read_csv('{events_csv.as_posix()}')")
    con.close()

    counts = {t: sum(e["event_type"] == t for e in events) for t in ("signup", "switch", "cancel")}
    print(f"{len(customers)} synthetic customers, {len(events)} events: {counts}")


if __name__ == "__main__":
    main()
