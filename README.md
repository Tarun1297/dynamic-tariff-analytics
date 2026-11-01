# dynamic-tariff-analytics

Did a normal household in Hamburg save money on a dynamic electricity tariff
compared with a fixed tariff, month by month? And what does that mean for a
provider's revenue and active contracts?

The full README follows in Phase 11. This file starts with the limits, so they
are recorded when each assumption is made.

## Limitations

The prices, grid fees, levies, taxes and the load profile are real. The fixed
price, the dynamic markup, the base fees and all customer data are
assumptions. The assumptions decide the size of the result, and one of them
can change its direction.

### What is real and what is assumed

| Input | Real or assumed | Source |
|---|---|---|
| Day-ahead prices, DE-LU | Real | ENTSO-E |
| Grid fees, Hamburg | Real | Hamburger Energienetze price sheets 2025 and 2026 |
| Levies, electricity tax, VAT, concession fee | Real | netztransparenz.de, gesetze-im-internet.de |
| Household load profile H25 | Real, but an average | BDEW, 2025 profiles |
| Fixed price 32.0 ct/kWh and 12.00 EUR per month | Assumed | Comparison sites, October 2026 |
| Dynamic markup 2.0 ct/kWh and 6.00 EUR per month | Assumed | Typical range of dynamic offers |
| Customers, contracts, switches, cancellations | Synthetic | `scripts/generate_crm.py`, random seed 42 |

### The fixed price decides the result

A first rough comparison, before the full models, gives these gaps. A positive
value means that the dynamic tariff costs more, in gross ct/kWh.

| Scenario | 2025 | Jan to Sep 2026 |
|---|---|---|
| As assumed: fixed 32.0, markup 2.0 | +3.9 | +3.1 |
| Markup 0 instead of 2.0 | +1.9 | +1.1 |
| Fixed 35.0, closer to an average contract | +0.9 | +0.1 |
| Fixed price for 2025 raised by the higher 2025 grid fee | +1.0 | +3.1 |
| Basic supply, about 42 ct/kWh | -6.1 | -6.9 |

- Each extra ct/kWh on the fixed price closes the gap by 1 ct/kWh. The gap
  is only 3 to 4 ct/kWh, so a realistic change in this one value almost
  removes it.
- Against a good fixed offer, a household that cannot move its consumption
  pays a little more on the dynamic tariff. Against basic supply, it saves
  6 to 7 ct/kWh.
- The final result is therefore a range, not one number.

### Other limits

- One fixed price covers 2025 and 2026. It comes from October 2026 offers.
  The grid fee was higher in 2025, so a fixed contract signed then probably
  cost more. This choice favours the fixed tariff.
- Every household follows the H25 profile exactly. No real smart-meter data
  is used. A household that uses more at night or at midday gains on a
  dynamic tariff. A household with a larger evening peak loses.
- The H25 profile comes from 2018 and 2019 data, with dynamization applied.
  It does not reflect newer patterns, such as more home office.
- The fee for the smart meter that a dynamic tariff needs is not modelled.
  It counts against the dynamic tariff.
- The section 14a grid fee modules are not applied, because a normal
  household has no controllable device. They apply to the EV in Phase 12.
- The analysis covers one city, Hamburg, with its grid fees and its
  concession fee. Other cities have different grid fees.
- The 2027 grid fees are the operator's provisional values, used only as
  guidance.

### Limits of the synthetic customer data

- All customer data is synthetic. The provider metrics show what the
  pipeline can measure, not how a real provider performs.
- The churn rule is an assumption. The base rate is 1.0 % per month. For a
  dynamic customer, it rises by 0.25 percentage points for each ct/kWh of
  extra cost over the fixed tariff in the month before. The link between expensive months and
  cancellations is therefore built in on purpose. A dashboard that shows it
  confirms the rule, not real customer behaviour.
- The churn rule uses a rough monthly cost per kWh in the script. The full
  cost model in dbt is more exact, so the two can differ slightly.
- Yearly use is spread evenly between 2,000 and 4,000 kWh. 70 % of customers
  start on the dynamic tariff, and 1 % of active customers switch tariff each
  month. These values are assumptions.
