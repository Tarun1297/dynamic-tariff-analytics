"""Load DE-LU day-ahead prices from ENTSO-E into raw.day_ahead_prices.

Run from the repo root: python -m pipelines.load_prices
Months that are already loaded are skipped, so a second run makes no API calls.
"""
import os

import dlt
import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient

ZONE = "DE_LU"
FIRST_MONTH = "2025-01"
LAST_MONTH = "2026-09"


@dlt.resource(
    table_name="day_ahead_prices",
    write_disposition="merge",
    primary_key="interval_start_utc",
)
def day_ahead_prices(client: EntsoePandasClient):
    loaded_months = dlt.current.resource_state().setdefault("loaded_months", [])

    for month in pd.period_range(FIRST_MONTH, LAST_MONTH, freq="M"):
        if str(month) in loaded_months:
            continue

        start = month.start_time.tz_localize("Europe/Berlin")
        end = (month + 1).start_time.tz_localize("Europe/Berlin")
        prices = client.query_day_ahead_prices(ZONE, start=start, end=end)
        # The client also returns the price at `end`. Keep start <= t < end,
        # so neighbouring months do not share a row.
        prices = prices[(prices.index >= start) & (prices.index < end)]

        yield [
            {
                "interval_start_utc": ts.tz_convert("UTC").to_pydatetime(),
                "price_eur_mwh": float(price),
                "bidding_zone": ZONE,
            }
            for ts, price in prices.items()
        ]
        loaded_months.append(str(month))


if __name__ == "__main__":
    load_dotenv()
    client = EntsoePandasClient(api_key=os.environ["ENTSOE_API_KEY"])
    pipeline = dlt.pipeline(
        pipeline_name="entsoe_prices",
        destination=dlt.destinations.duckdb("data/warehouse.duckdb"),
        dataset_name="raw",
    )
    print(pipeline.run(day_ahead_prices(client)))
