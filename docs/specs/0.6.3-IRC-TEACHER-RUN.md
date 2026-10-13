# Ethan — Hesperia 0.6.3: IRC-visible Teacher application run

**Date:** 2026-06-14  
**Entity:** Ethan (governance)  
**Status:** TRIAGED — Grace H063-00..49 on [active.md](../active.md)  
**Register:** [H063-2026-REGISTER.md](H063-2026-REGISTER.md)  
**Builds on:** 0.6.2 sealed (KSI-P0..P3, packet schema, no live Teacher)  
**Does not reopen:** 0.6.2 engine math, corpus layout, or HINS prod hygiene

---

## 1. Version boundary (do not mix)

| Release | What it is | What it is NOT |
|---------|------------|----------------|
| **0.6.2** (sealed) | Deterministic engine + KSI inspection + **Teacher packet serializer** + gate/sandbox **schemas** | Live OpenAI Teacher; IRC product run; MySQL ledger |
| **0.6.3** (this spec) | **Application-level** end-to-end run: Russian TFP input → Hesperia activation → IRC-visible JSON → OpenAI **parameter-only** Teacher → MySQL adjustment ledger | Sandbox auto-apply to prod graph; Inspector UI (KSI-19) |
| **0.7.0** (deferred) | Sandbox **apply** loop, proposal merge to CD/graph files, Session Inspector Pane 2 | Replacing 0.6.3 IRC contract |

**Argue:** Live LLM was tagged 0.7.0 / KSI-P4 in exit criteria. **Propose:** **0.6.3** = operator-facing **IRC Teacher Run** (live call + persistence + full trace). **0.7.0** keeps graph **write** + sandbox replay apply only.

---

## 2. Application run road (operator)

**Input:** Russian scientific / TFP statement (one utterance).  
**Surface:** Tersagor Telegram → IRC (you see everything).  
**Language:** `lang=ru` on all operator-facing envelopes; corpus + CD labels in Russian where allowlisted.

```
Operator (TG, RU statement)
    → tersagor approval-gateway / mesh
    → IRC #hesperia-teacher (or #agents-debug)  [trace: RUN_START]
    → hybrid_retriever.retrieve()
         → hesperia /analyze (engine_result)
         → post: geometry (IPoV, GTP)
         → post: KSI (Φ_e, residuals, incidents, phi_trace)
         → optional: reflection audit (off by default in 0.6.3)
    → IRC  [trace: ENGINE_ENVELOPE]  full LLM-readable JSON
    → build teacher_packet (sanitized per H62-064) + run_envelope metadata
    → OpenAI strict JSON schema (values only, no chat)
    → IRC  [trace: TEACHER_REQUEST, TEACHER_RESPONSE]
    → MySQL hesperia: persist run + snapshot + proposals
    → IRC  [trace: REWEIGHT_PREVIEW]  scalar deltas only
```

**Tersagor command (proposed):** `!agent hesperia teach` or preset `hesperia_clinical` plain text with `HESPERIA_KSI_ENABLED=1` + `HESPERIA_KSI_LLM_TEACHER=1`.

**Pipeline order (already wired 0.6.2):** `retrieve` → geometry → KSI → (reflection off in 0.6.3 default).

---

## 3. JSON envelopes

### 3.1 `engine_run_envelope` (IRC + storage — operator full view)

Single document the operator and LLM context builder share. Large blobs may be IRC-chunked with same `correlation_id`.

```json
{
  "schema": "hesperia.engine_run_envelope.v063",
  "lang": "ru",
  "correlation_id": "cid-…",
  "run_id": "uuid",
  "input": {
    "text_ru": "…",
    "kind": "tfp_scientific_statement"
  },
  "engine": {
    "hesperia_ref": "git-sha",
    "tersagor_ref": "git-sha",
    "analyze_trace_id": "…",
    "propagation_trace": [],
    "areas": {},
    "families": {},
    "tfp_vector": {},
    "invariant_activation": {},
    "interior_pov": {},
    "gtp_coherence": {},
    "corpus_activations": [],
    "roads": []
  },
  "ksi": {
    "version": "0.1",
    "incidents": [],
    "missing_bridges": [],
    "phi_trace": {}
  },
  "parameters": {
    "W_e": [],
    "R_e": [],
    "thresholds": {},
    "ksi_config_ref": "assets/data/ksi/ksi_config_v01.json"
  }
}
```

`roads` = ordered activation path (propagation_trace + GTP path ids). `corpus_activations` = concept/session activation summary with **ids + scalars**, not raw book text.

### 3.2 `teacher_request` (to OpenAI — sanitized)

Subset of §12.1 [SPEC-HESPERIA-KOLMOGOROV-SEMANTIC-INSPECTION-v0_1.md](SPEC-HESPERIA-KOLMOGOROV-SEMANTIC-INSPECTION-v0_1.md). **No `input.text_ru`** in Teacher request (H62-064). Russian only in **CD allowlisted labels** attached to `concept_id`.

### 3.3 `teacher_response` (from OpenAI — 0.6.3 contract)

**Operator rule:** MODEL returns **only fixable parameters and values**. No reasoning prose, no chat, no `message`, no `justification`.

```json
{
  "schema": "hesperia.teacher_response.v063",
  "lang": "ru",
  "proposals": [
    {
      "action": "update_edge_weight",
      "source": "REJECTION",
      "target": "WITHDRAWAL",
      "type": "activates",
      "W_e_current": 0.0,
      "W_e_proposed": 0.7,
      "confidence": 0.85
    },
    {
      "action": "update_cd_field",
      "concept_id": "SHAME",
      "field": "threshold",
      "value_current": 0.4,
      "value_proposed": 0.55,
      "confidence": 0.78
    }
  ]
}
```

OpenAI: `response_format` JSON schema strict; system prompt in Russian: *«Верни только JSON proposals. Без объяснений и текста.»*

---

## 4. IRC observability contract

| IRC message type | Channel | Content |
|------------------|---------|---------|
| `RUN_START` | `#hesperia-teacher` | `correlation_id`, `run_id`, input hash, `lang=ru` |
| `ENGINE_ENVELOPE` | same | Full `engine_run_envelope` (chunk if >4k) |
| `TEACHER_REQUEST` | same | Sanitized `teacher_request` JSON |
| `TEACHER_RESPONSE` | same | `teacher_response` JSON |
| `REWEIGHT_PREVIEW` | same | Computed deltas per proposal (no graph write) |
| `RUN_DONE` | same | `status`, MySQL ids |

**Security:** IRC is operator-trusted LAN mesh; still no API keys in IRC bodies. Ref: [cluster/tersagor/OPERATOR-HEALTH.md](../cluster/tersagor/OPERATOR-HEALTH.md).

---

## 5. MySQL schema (`hesperia` database on prichindel `mysql_db`)

New database **`hesperia`** (or schema prefix `h063_`). UTF8MB4 for Russian labels in allowlisted columns only.

```sql
CREATE DATABASE IF NOT EXISTS hesperia
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- One operator-triggered run
CREATE TABLE hesperia_teacher_run (
  run_id            CHAR(36) PRIMARY KEY,
  correlation_id    VARCHAR(128) NOT NULL,
  lang              CHAR(2) NOT NULL DEFAULT 'ru',
  input_text_ru     MEDIUMTEXT NOT NULL,
  input_kind        VARCHAR(64) NOT NULL DEFAULT 'tfp_scientific_statement',
  engine_envelope   JSON NOT NULL,
  teacher_request   JSON NOT NULL,
  teacher_response  JSON NULL,
  irc_channel       VARCHAR(64) NULL,
  status            ENUM('started','engine_ok','teacher_ok','teacher_fail','stored') NOT NULL,
  hesperia_git_sha  VARCHAR(40) NULL,
  tersagor_git_sha  VARCHAR(40) NULL,
  openai_model      VARCHAR(64) NULL,
  created_at        TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_corr (correlation_id),
  INDEX idx_created (created_at)
);

-- Snapshot of relational network state at run time (matrix edges)
CREATE TABLE hesperia_edge_snapshot (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  run_id            CHAR(36) NOT NULL,
  source_concept_id VARCHAR(128) NOT NULL,
  target_concept_id VARCHAR(128) NOT NULL,
  relation_type     VARCHAR(64) NOT NULL,
  W_e               DECIMAL(12,6) NOT NULL,
  R_e               DECIMAL(12,6) NULL,
  Q_e               DECIMAL(12,6) NULL,
  C_e               DECIMAL(12,6) NULL,
  D_e               DECIMAL(12,6) NULL,
  K_e               DECIMAL(12,6) NULL,
  phi_sat           DECIMAL(12,6) NULL,
  area_id           VARCHAR(128) NULL,
  family_id         VARCHAR(128) NULL,
  FOREIGN KEY (run_id) REFERENCES hesperia_teacher_run(run_id),
  INDEX idx_run (run_id),
  INDEX idx_edge (source_concept_id, target_concept_id, relation_type)
);

-- Concept activation row per run (observed vs expected)
CREATE TABLE hesperia_activation_snapshot (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  run_id            CHAR(36) NOT NULL,
  concept_id        VARCHAR(128) NOT NULL,
  label_ru          VARCHAR(255) NULL,
  area_id           VARCHAR(128) NULL,
  family_id         VARCHAR(128) NULL,
  observed          DECIMAL(12,6) NOT NULL,
  expected          DECIMAL(12,6) NULL,
  residual          DECIMAL(12,6) NULL,
  incident_type     VARCHAR(64) NULL,
  FOREIGN KEY (run_id) REFERENCES hesperia_teacher_run(run_id),
  INDEX idx_run_concept (run_id, concept_id)
);

-- LLM proposals (pending until 0.7.0 apply)
CREATE TABLE hesperia_proposal (
  proposal_id       CHAR(36) PRIMARY KEY,
  run_id            CHAR(36) NOT NULL,
  seq               INT NOT NULL,
  action            VARCHAR(32) NOT NULL,
  target_type       ENUM('edge','concept','cd_field','bridge') NOT NULL,
  payload           JSON NOT NULL,
  confidence        DECIMAL(6,4) NULL,
  incident_ref      VARCHAR(128) NULL,
  status            ENUM('pending','accepted','rejected','sandbox_pass','sandbox_fail') DEFAULT 'pending',
  created_at        TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
  FOREIGN KEY (run_id) REFERENCES hesperia_teacher_run(run_id),
  INDEX idx_run_status (run_id, status)
);

-- Reweighting preview / future apply audit
CREATE TABLE hesperia_reweight_event (
  event_id          CHAR(36) PRIMARY KEY,
  run_id            CHAR(36) NOT NULL,
  proposal_id       CHAR(36) NULL,
  parameter_key     VARCHAR(128) NOT NULL,
  value_before      DECIMAL(12,6) NULL,
  value_after       DECIMAL(12,6) NOT NULL,
  applied           TINYINT(1) NOT NULL DEFAULT 0,
  operator_subject  VARCHAR(255) NULL,
  created_at        TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
  FOREIGN KEY (run_id) REFERENCES hesperia_teacher_run(run_id),
  FOREIGN KEY (proposal_id) REFERENCES hesperia_proposal(proposal_id)
);
```

**Host:** prichindel Docker `mysql_db`; credentials in `/root/.secrets/` (Abelard). Not Oracle APEX `prichindelbd`.

---

## 6. What to build (Grace triage → H063-*)

| ID | Owner | Deliverable |
|----|-------|-------------|
| H063-00 | Grace | Wave meta + ratify this spec |
| H063-01 | Ethan | Ratify 0.6.3 vs 0.7.0 split; amend exit-criteria footnote |
| H063-02 | Felix | `engine_run_envelope` builder in tersagor after `hybrid_retriever` |
| H063-03 | Felix | OpenAI Teacher client — strict `teacher_response.v063`, no prose |
| H063-04 | Felix | IRC emitter (`RUN_*` message types) on `#hesperia-teacher` |
| H063-05 | Gena | `schemas/teacher_response_v063.json` + extend `ksi_proposal_schema` |
| H063-06 | Abelard | MySQL `hesperia` DB + migrations; secrets |
| H063-07 | Felix | Persist run/snapshots/proposals from IRC path |
| H063-08 | Sophia | 0.6.3 boundary: IRC may show `input_text_ru`; Teacher request still H62-064 |
| H063-09 | Marcus | Runbook: Russian statement → IRC trace → MySQL query |
| H063-10 | Daniel | Gate: proposals `pending` only — no auto-apply (0.7.0) |

---

## 7. Operator acceptance (Ethan)

0.6.3 is **done** when:

1. Russian statement in TG produces IRC trace with **engine JSON + teacher JSON** visible.
2. OpenAI response validates against `teacher_response.v063` with **zero** free-text fields outside schema.
3. MySQL row exists per run with edge + activation snapshots and proposals.
4. **No** silent graph file mutation (reweighting preview only in IRC + `hesperia_reweight_event.applied=0`).

---

SIGNED: Team lead (Ethan) | 0.6.3 IRC Teacher application run | 2026-06-14 | governance draft
