"""Checks for scripts/generate_crm.py. They need no database, so CI can run them."""
import generate_crm as crm

# A fixed gap of 3 ct/kWh in every month stands in for the real prices.
GAPS = {m.strftime("%Y-%m"): 3.0 for m in crm.month_starts()}


def write_both(tmp_path, customers, events):
    crm.write_csv(tmp_path / "customers.csv", customers, list(customers[0]))
    crm.write_csv(tmp_path / "contract_events.csv", events, list(events[0]))
    return [(tmp_path / f).read_bytes() for f in ("customers.csv", "contract_events.csv")]


def test_two_runs_give_identical_files(tmp_path):
    first = write_both(tmp_path / "a", *crm.simulate(GAPS))
    second = write_both(tmp_path / "b", *crm.simulate(GAPS))
    assert first == second


def test_another_seed_gives_other_data():
    assert crm.simulate(GAPS, seed=1) != crm.simulate(GAPS, seed=2)


def test_every_customer_has_one_signup():
    customers, events = crm.simulate(GAPS)
    assert len(customers) == crm.N_CUSTOMERS
    assert sum(e["event_type"] == "signup" for e in events) == crm.N_CUSTOMERS


def test_event_order_per_customer():
    _, events = crm.simulate(GAPS)
    by_customer = {}
    for e in events:
        by_customer.setdefault(e["customer_id"], []).append(e)

    for history in by_customer.values():
        types = [e["event_type"] for e in history]
        assert types[0] == "signup"
        assert types.count("cancel") <= 1
        if "cancel" in types:
            assert types[-1] == "cancel"
        for before, after in zip(history, history[1:]):
            assert before["event_date"] <= after["event_date"]
            if after["event_type"] == "switch":
                assert after["tariff"] != before["tariff"]


def test_all_dates_inside_the_period():
    _, events = crm.simulate(GAPS)
    dates = [e["event_date"] for e in events]
    assert min(dates) >= crm.FIRST_DAY.isoformat()
    assert max(dates) <= crm.LAST_DAY.isoformat()


def test_all_rows_are_labelled_synthetic():
    customers, events = crm.simulate(GAPS)
    assert {r["data_origin"] for r in customers + events} == {"synthetic"}
