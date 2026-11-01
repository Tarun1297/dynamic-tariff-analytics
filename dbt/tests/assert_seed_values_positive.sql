-- Fails if any price, fee or profile value is zero or negative.
select 'tariff_components' as seed_name, component as item_key, value
from {{ ref('tariff_components') }}
where value <= 0

union all

select 'grid_fees', item, value
from {{ ref('grid_fees') }}
where value <= 0

union all

select 'tariffs', tariff || ' ' || item, value
from {{ ref('tariffs') }}
where value <= 0

union all

select 'bdew_load_profiles', day_type || ' ' || interval_start, kwh_per_1m_kwh_year
from {{ ref('bdew_load_profiles') }}
where kwh_per_1m_kwh_year <= 0
