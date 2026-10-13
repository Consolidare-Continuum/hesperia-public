# Docker bundle

Build the `v0.6.0` shipping image from the sealed baseline.
Use shipping requirements only.
Keep dicts, corpus, and Chroma outside the image.

## Build

- Run `python3 tools/release/build_docker_bundle_v0_6_0.py`.
- Expect image tag `hesperia-api:0.6.0`.
- Expect tar output `release/v0.6.0/hesperia-api-v0.6.0.tar`.

## Check

- Run `/health`.
- Run `/analyze` with canonical input smoke text.
- Verify forbidden dirs are absent from `/app`.
- Save tar.
- Record SHA256 and image id.

## Runtime

- Pass `HESPERIA_LICENSE_SKIP=1` only for local verification.
- Mount external dicts, corpus, and Chroma state separately.
- Do not bake mutable runtime state into the image.
