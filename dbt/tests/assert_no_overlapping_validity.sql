-- Fails if two rows of the same item are valid on the same day.
-- An empty valid_until means the row is still valid.
with periods as (
    select
        'tariff_components' as seed_name,
        component as item_key,
        valid_from,
        coalesce(cast(valid_until as date), date '9999-12-31') as valid_until
    from {{ ref('tariff_components') }}

    union all

    select
        'grid_fees',
        item || ' ' || coalesce(time_from, ''),
        valid_from,
        coalesce(cast(valid_until as date), date '9999-12-31')
    from {{ ref('grid_fees') }}

    union all

    select
        'tariffs',
        tariff || ' ' || item,
        valid_from,
        coalesce(cast(valid_until as date), date '9999-12-31')
    from {{ ref('tariffs') }}
)

select
    a.seed_name,
    a.item_key,
    a.valid_from as first_from,
    b.valid_from as second_from
from periods as a
inner join periods as b
    on
        a.seed_name = b.seed_name
        and a.item_key = b.item_key
        and a.valid_from < b.valid_from
        and a.valid_until >= b.valid_from
