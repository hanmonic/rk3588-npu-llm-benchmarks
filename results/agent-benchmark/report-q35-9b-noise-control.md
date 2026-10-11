# rkllm-bench report

Generated 2026-10-11T03:54:53Z from `noise-control` (runs: 1011T0335-01f6ca).

Times are wall-clock as seen by the client unless marked srv (server-reported `usage.rkllm`). Task wall = sum of the task's request times. Time to useful result = task wall up to the turn where the task's success condition first held (passed tasks only). Prefill/turn = tokens actually prefilled (not served from KV cache).

## Time to useful result

Mean seconds from the first request to the turn where the task was solved, over passed tasks (pass count in brackets).

| model | scenario | cache on | cache off |
|---|---|---|---|
| q35-9b | hard-multistep | 58.1s (4/4) | n/a |
| q35-9b | house-batch | 165.7s (3/4) | n/a |

## q35-9b

| scenario | cache | pass | score | turns/task | task wall s (p50) | turn wall s | TTFT srv p50/p90 ms | TTFT client p50 ms | prefill/turn | cached/turn | hit | prefill t/s | decode t/s | max ctx | malformed | unknown | errors | cache events | queue s | load s | stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hard-multistep | on | 4/4 | 1.00 | 2.2 | 65.8 (46.7) | 29.2 | 3294/36365 | 3811 | 66 | 1320 | 95% | 28.7 | 2.51 | 1548 | 0 | 0 | 0 | cold:4 hit:5 | 0.0 | - | done:1 task_stop:3 |
| house-batch | on | 3/4 | 0.94 | 2.2 | 215.9 (205.8) | 95.9 | 10236/35296 | 26122 | 246 | 1377 | 85% | 34.3 | 2.39 | 1913 | 0 | 0 | 0 | cold:4 hit:5 | 0.0 | - | done:4 |

## TTFT by cache event

`restored` rows in the interleaved scenario are the session park/restore cost.

| model | scenario | cache | event | n | TTFT srv mean ms | p50 | p90 | prefill mean | cached mean |
|---|---|---|---|---|---|---|---|---|---|
| q35-9b | hard-multistep | on | cold | 4 | 10275 | 1667 | 36365 | 30 | 1292 |
| q35-9b | hard-multistep | on | hit | 5 | 3372 | 3404 | 3692 | 95 | 1342 |
| q35-9b | house-batch | on | cold | 4 | 11322 | 3307 | 35296 | 77 | 1278 |
| q35-9b | house-batch | on | hit | 5 | 11015 | 14082 | 14540 | 380 | 1456 |

