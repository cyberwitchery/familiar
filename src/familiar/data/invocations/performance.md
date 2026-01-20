task: identify performance hotspots, propose optimizations, and measure improvements.

## inputs

- $1 `target` (required): file path, function name, or scope to analyze
- $2 `metric` (optional): `time`, `memory`, `cpu`, `io`. default: `time`

## preconditions

STOP and ask if:
- no profiling data exists—do not optimize without measuring first
- no way to benchmark (no tests, no profiler)
- the "slow" code hasn't been measured (gut feeling is not data)

## process

1. **profile**: identify actual hotspots with data
2. **measure**: establish reproducible baseline
3. **analyze**: understand *why* it's slow
4. **propose**: suggest optimizations with tradeoffs
5. **implement**: change incrementally
6. **verify**: measure improvement, confirm correctness

## what to look for

- functions taking disproportionate time (>10%)
- excessive allocations or GC pressure
- I/O bottlenecks (disk, network, DB)
- repeated work that could be cached
- O(n²) hiding in loops

## optimization priority

1. **algorithmic**: better data structures, caching, batching
2. **I/O**: batch queries, connection pooling, async
3. **implementation**: reduce allocations, avoid copies, early returns

## anti-patterns

- optimizing without profiling
- optimizing startup code or cold paths
- sacrificing readability for marginal gains

## output

```
## target
<what was analyzed>

## profiling
<tool and method>

## hotspots
1. [file:line] <function> - <time> (<% of total>)

## baseline
<benchmark command and result>

## proposed optimization
- change: <what>
- expected: <improvement estimate>
- tradeoff: <cost>

## results
| metric | before | after | improvement |
|--------|--------|-------|-------------|
| time   | X ms   | Y ms  | Z%          |

## verification
- [ ] tests pass
- [ ] improvement is statistically significant
```
