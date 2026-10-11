# rkllm-bench report

Generated 2026-10-11T03:35:39Z from `noise-append` (runs: 1011T0312-5c2ec8).

Times are wall-clock as seen by the client unless marked srv (server-reported `usage.rkllm`). Task wall = sum of the task's request times. Time to useful result = task wall up to the turn where the task's success condition first held (passed tasks only). Prefill/turn = tokens actually prefilled (not served from KV cache).

## Time to useful result

Mean seconds from the first request to the turn where the task was solved, over passed tasks (pass count in brackets).

| model | scenario | cache on | cache off |
|---|---|---|---|
| q35-9b | hard-multistep | 75.4s (3/4) | n/a |
| q35-9b | house-batch | 142.6s (2/4) | n/a |

## q35-9b

| scenario | cache | pass | score | turns/task | task wall s (p50) | turn wall s | TTFT srv p50/p90 ms | TTFT client p50 ms | prefill/turn | cached/turn | hit | prefill t/s | decode t/s | max ctx | malformed | unknown | errors | cache events | queue s | load s | stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hard-multistep | on | 3/4 | 0.75 | 2.0 | 85.6 (59.6) | 42.8 | 3084/38278 | 3427 | 60 | 646 | 92% | 21.9 | 2.30 | 1333 | 0 | 0 | 0 | cold:4 restored:4 | 0.0 | - | task_stop:4 |
| house-batch | on | 2/4 | 0.92 | 2.0 | 248.4 (231.7) | 124.2 | 10093/35828 | 25578 | 270 | 639 | 70% | 29.1 | 2.46 | 1378 | 0 | 0 | 0 | cold:4 restored:4 | 0.0 | - | done:4 |

## TTFT by cache event

`restored` rows in the interleaved scenario are the session park/restore cost.

| model | scenario | cache | event | n | TTFT srv mean ms | p50 | p90 | prefill mean | cached mean |
|---|---|---|---|---|---|---|---|---|---|
| q35-9b | hard-multistep | on | cold | 4 | 11105 | 1837 | 38278 | 30 | 1292 |
| q35-9b | hard-multistep | on | restored | 4 | 3954 | 3257 | 6049 | 89 | 0 |
| q35-9b | house-batch | on | cold | 4 | 11417 | 3309 | 35828 | 77 | 1278 |
| q35-9b | house-batch | on | restored | 4 | 16122 | 14226 | 25577 | 464 | 0 |

