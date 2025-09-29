-- Singular test: ensure (season, week, gsis_id) is unique
with dupe as (
  select season, week, gsis_id, count(*) as c
  from {{ ref('stg_nflverse__weekly') }}
  group by 1,2,3
  having count(*) > 1
)
select * from dupe
;
