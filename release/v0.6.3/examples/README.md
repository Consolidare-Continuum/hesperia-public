# Hesperia 0.6.3 — example outputs

Out-of-context demonstration artifacts. Safe for public archive; not live patient data.

| File | What it shows |
|------|----------------|
| `example_analyze_shipping_output.json` | Engine `/analyze` minimal + API v1 envelope (offline fixture) |
| `example_engine_run_envelope_v063.json` | Full IRC `ENGINE_ENVELOPE` for 0.6.3 Teacher run |
| `example_teacher_response_v063.json` | OpenAI Teacher strict JSON — numeric proposals only |
| `example_reweight_preview.json` | Scalar deltas before graph apply (`applied=0`) |
| `example_irc_trace.jsonl` | Lounge-visible trace sequence RUN_START → RUN_DONE |
| `example_mysql_teacher_run_row.json` | MySQL ledger row shape after persist |

**Live path:** tersagor `0149120` + `TERSAGOR_HESPERIA_IRC_TEACHER=1` → writes real rows; these files are reference only.
