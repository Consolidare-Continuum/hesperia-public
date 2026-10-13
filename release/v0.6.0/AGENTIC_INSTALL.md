# Agentic install

Install `HESPERIA 0.6.0` in this order.
Do not improvise the order.
Do not bake mutable data into the image.

## Inputs

- Docker image tag: `hesperia-api:0.6.0`
- Docker tar: `release/v0.6.0/hesperia-api-v0.6.0.tar`
- Required dict pack: `v0_6_0_clr_v052_2`
- Required external state: dicts, corpus, Chroma

## Prepare host

- Create host dirs for `dicts`, `corpus`, `chroma`, and `runtime-output`.
- Keep them outside the repo checkout.
- Keep ownership writable by the runtime user.

## Prepare externals

- Build dict pack `v0_6_0_clr_v052_2` exactly.
- Place dict files under `assets/calibration/dicts/v0_6_0_clr_v052_2/` inside the runtime mount root.
- Prepare corpus manifests and corpus files.
- Prepare or ingest Chroma collections before retrieval runs.

## Load image

- Load tar with `docker load -i release/v0.6.0/hesperia-api-v0.6.0.tar`.
- Verify image tag `hesperia-api:0.6.0` exists.

## Run check container

- Start container with external mounts only.
- Expose port `8000`.
- Use `HESPERIA_LICENSE_SKIP=1` only for local smoke.
- Use `HESPERIA_EXPOSE_VERSION=1` for verification only.

## Verify

- Call `GET /health`. Expect `status=ok`.
- Call `GET /version`. Expect `system_version=0.6.0`.
- Call `POST /analyze` with canonical smoke text.
- Verify response contains `system_version`, `schema_version`, `build_id`, `calibration_profile`.

## Gate

- Require `final_gate_status.json` sealed result.
- Require `docker_bundle_verification.json` with `health_ok=true`.
- Require `docker_bundle_verification.json` with `analyze_ok=true`.
- Require forbidden dev dirs absent from `/app`.

## Production rule

- Keep dicts external.
- Keep corpus external.
- Keep Chroma external.
- Replace local verification env with production license/env policy before ship.
