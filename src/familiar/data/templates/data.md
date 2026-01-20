# data engineering

data mistakes corrupt datasets, cause incorrect analyses, or violate privacy. verify transformations and protect against injection.

## critical constraints

STOP and ask before:
- modifying production database schemas
- running DELETE/UPDATE/TRUNCATE on production
- changing ETL logic that affects downstream consumers
- processing PII or sensitive data

NEVER:
- concatenate user input into SQL—always use parameterized queries
- execute unreviewed SQL against production
- hardcode credentials
- modify data in place without rollback ability

## sql safety

```python
# SAFE: parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# DANGEROUS: string concatenation (SQL injection)
query = f"SELECT * FROM users WHERE id = {user_id}"
```

for transactional DBs (postgres, mysql), use transactions:
```sql
BEGIN;
  UPDATE orders SET status = 'done' WHERE id = 123;
ROLLBACK;  -- verify before COMMIT
```

for analytical DBs (BigQuery, Snowflake), prefer immutable patterns—write new partitions rather than update in place.

## dataframes

before transforming: check shape, dtypes, nulls
after transforming: validate row counts, uniqueness, expected values
make copies for destructive operations

## pipelines

- **idempotent**: running twice = same result
- **atomic**: all-or-nothing, no partial updates
- **validated**: check data quality at entry and exit

## schema changes

1. document current schema and consumers
2. ensure backwards compatibility or coordinate
3. test on copy of production data
4. have rollback plan

## verification

- row counts match expectations
- no unexpected NULLs
- keys remain unique
- downstream queries still work
