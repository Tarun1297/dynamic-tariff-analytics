-- Fails if a month and day type does not have exactly 96 different quarter-hours.
-- 12 months x 3 day types x 96 quarter-hours = 3,456 rows.
select
    profile,
    month,
    day_type,
    count(*) as row_count,
    count(distinct interval_start) as distinct_quarter_hours
from {{ ref('bdew_load_profiles') }}
group by profile, month, day_type
having count(*) <> 96 or count(distinct interval_start) <> 96
