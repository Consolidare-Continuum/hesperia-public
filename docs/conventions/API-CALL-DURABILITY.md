# Rule: every paid/rate-limited external API call must survive a crash

**Status:** binding, effective 2026-08-19. Applies to any code in this repo that calls an
external API in a loop — OpenAI today, anything else with the same shape later (another LLM
vendor, a paid embeddings API, etc).

## The rule

If a function makes more than one call to a paid or rate-limited external API in sequence, each
call's result **must be durably persisted to disk before the next call starts** — not just
accumulated in memory, not just a running count, and not only written once at the very end of the
loop. A process getting killed between calls (session/harness restart, OOM, host reboot, `kill`)
must cost at most the one in-progress call, never the accumulated work of the whole run.

"Durably persisted" means: written to a real file on the actual filesystem (not `/tmp` unless the
job is genuinely disposable), flushed and `fsync`'d before the function returns or raises, in a
location a *different* process — possibly hours later, possibly a different agent session
entirely — can find and use without needing the original caller's in-memory state.

## Why this exists

2026-08-19: a ~6-8h, multi-hundred-call `gpt-5-mini` batch run
(`tools/dict_calibration/ru_tfp_corpus_align.py`) got killed by a session/harness restart between
pass 1 and pass 2. Pass 1 alone was 294 real paid API calls (~$0.46) that had already found real,
usable results — but the tool only ever wrote *summary counts* per pass, never the actual
accumulated links, which lived in memory until the very end of the whole run. All of pass 1's real
output was unrecoverable. Real money spent, zero usable output, for a gap that a few lines of
"write the result before moving on" code would have closed.

## How it's enforced here

`tools/dict_calibration/openai_json.py::chat_json()` — the shared entrypoint essentially all
OpenAI-calling tools in this repo route through — appends **every** call's result (success or
JSON-parse failure) to a call ledger before returning or raising:

- Ledger location: `HESPERIA_CALIB_CALL_LEDGER` env var if set, else
  `outputs/openai_call_ledger.jsonl` at repo root.
- `tools/dict_calibration/run_pipeline.py`'s long-running entrypoints (`ru-tfp-align`, `run-all`)
  set this automatically to `<workdir>/call_ledger.jsonl`, so each run's ledger sits next to its
  other outputs.
- Each line: `{ts, model, call_tag, user_preview, content, usage}` — `content` is the raw model
  output, enough to reconstruct what the call produced without re-calling the API. `call_tag` is
  an optional caller-supplied label (pass/batch/chunk identity) for readability; pass it whenever
  the call site has a natural identity to give.
- Write pattern: open in append mode, write one JSON line, `flush()`, `fsync()`, close — every
  call, not batched. This is the actual guarantee; a held-open file handle or buffered writer
  would defeat the point.

This means **any new tool that calls `chat_json()` inherits the ledger automatically** — no
per-tool opt-in needed. If you add a new OpenAI-calling loop that does *not* go through
`chat_json()` (there's a separate path today: `sphere.calibration.llm_calibration.
call_governed_calibration`, used by the diagnostics-only `tools/openai_calibration/
openai_calibrate_*.py` scripts — not yet covered by this ledger, a known gap), you must add
equivalent per-call persistence yourself, or route through `chat_json()` instead.

## What this does *not* require

- Automatic resume-from-ledger on restart. The ledger is forensic/recovery raw material — a human
  or agent can reconstruct progress from it, but no tool here auto-resumes from it yet. That's a
  reasonable future enhancement, not part of this rule.
- Persisting every intermediate in-memory transformation. Just the API call boundary — the
  expensive, non-reproducible-without-paying-again part.

## When launching a long/costly run

Beyond the ledger (which protects the *data*), also protect the *process* itself: launch fully
detached (`setsid nohup <command> > log 2>&1 < /dev/null & disown`), and verify with
`ps -p <pid> -o ppid` that `PPID` is `1` (reparented to init), not a shell in the calling session
— a session/harness restart can otherwise kill an OS process that had nothing wrong with it. Write
a short status file (PID, start time, expected duration, where to find real progress) into the
run's own workdir, not a session-scoped `/tmp` path, so a different session can pick it up later.
