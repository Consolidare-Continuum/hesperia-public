#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
VERSION_DOC = yaml.safe_load((REPO / "VERSION.yaml").read_text(encoding="utf-8")) or {}
VERSION = str(VERSION_DOC.get("system_version") or "")
RELEASE_DIR = REPO / "release" / f"v{VERSION}"
IMAGE_REPO = f"hesperia-api:{VERSION}"
TAR_NAME = f"hesperia-api-v{VERSION}.tar"
REQ_LOCK_NAME = "docker_requirements_used.txt"
VERIFY_NAME = "docker_bundle_verification.json"
MANIFEST_NAME = "docker_bundle_manifest.json"
BUILD_NOTE_NAME = "DOCKER_BUNDLE.md"
CONTAINER_NAME = f"hesperia_docker_check_{VERSION.replace('.', '_')}"


def _run(cmd: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO,
        check=check,
        text=True,
        capture_output=capture,
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return int(s.getsockname()[1])


def _http_json(url: str, *, payload: dict | None = None, timeout: float = 3.0) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_http_ok(base_url: str, *, timeout_s: float = 40.0) -> tuple[bool, str]:
    start = time.monotonic()
    last_err = "not_started"
    while time.monotonic() - start < timeout_s:
        try:
            payload = _http_json(f"{base_url}/health", timeout=2.0)
            if payload.get("status") == "ok":
                return True, "health ok"
            last_err = f"unexpected health payload: {payload!r}"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
        time.sleep(1.0)
    return False, last_err


def _docker_rm(name: str) -> None:
    subprocess.run(["docker", "rm", "-f", name], cwd=REPO, text=True, capture_output=True)


def _build_note() -> str:
    return f"""# Docker bundle

Build the `v{VERSION}` shipping image from the sealed baseline.
Use shipping requirements only.
Keep dicts, corpus, and Chroma outside the image.

## Build

- Run `python3 tools/release/build_docker_bundle_v0_6_0.py`.
- Expect image tag `hesperia-api:{VERSION}`.
- Expect tar output `release/v{VERSION}/{TAR_NAME}`.

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
"""


def main() -> int:
    if VERSION != "0.6.0":
        print(f"expected VERSION.yaml system_version 0.6.0, got {VERSION!r}", file=sys.stderr)
        return 1
    if shutil.which("docker") is None:
        print("docker is required", file=sys.stderr)
        return 1

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = RELEASE_DIR / TAR_NAME
    req_used = RELEASE_DIR / REQ_LOCK_NAME
    verify_path = RELEASE_DIR / VERIFY_NAME
    manifest_path = RELEASE_DIR / MANIFEST_NAME
    note_path = RELEASE_DIR / BUILD_NOTE_NAME

    req_used.write_text((REPO / "requirements" / "shipping.txt").read_text(encoding="utf-8"), encoding="utf-8")
    note_path.write_text(_build_note(), encoding="utf-8")

    fail_reason = ""
    build = _run(["docker", "build", "-f", "Dockerfile.shipping", "-t", IMAGE_REPO, "."], capture=True)
    image_id = _run(["docker", "image", "inspect", IMAGE_REPO, "--format", "{{.Id}}"]).stdout.strip()

    port = _free_port()
    _docker_rm(CONTAINER_NAME)
    run = _run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            CONTAINER_NAME,
            "-e",
            "HESPERIA_LICENSE_SKIP=1",
            "-e",
            "HESPERIA_EXPOSE_VERSION=1",
            "-p",
            f"127.0.0.1:{port}:8000",
            IMAGE_REPO,
        ],
        capture=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    health_ok, health_note = _wait_http_ok(base_url)
    analyze_payload = {}
    analyze_ok = False
    analyze_note = ""
    version_payload = {}
    absent_dirs: dict[str, bool] = {}
    logs_tail = ""
    try:
        if not health_ok:
            fail_reason = health_note
        else:
            version_payload = _http_json(f"{base_url}/version", timeout=4.0)
            try:
                analyze_payload = _http_json(
                    f"{base_url}/analyze",
                    payload={"text": "Justice and fairness support social order."},
                    timeout=20.0,
                )
            except urllib.error.HTTPError as exc:
                fail_reason = f"analyze_http_{exc.code}"
                body = exc.read().decode("utf-8", errors="replace")
                analyze_payload = {"_http_error": exc.code, "_body": body}
            analyze_ok = (
                isinstance(analyze_payload, dict)
                and analyze_payload.get("system_version") == VERSION
                and analyze_payload.get("schema_version") == "v1"
                and bool(analyze_payload.get("build_id"))
                and bool(analyze_payload.get("calibration_profile"))
            )
            if not fail_reason:
                analyze_note = "public envelope ok" if analyze_ok else "public envelope missing expected fields"
            else:
                analyze_note = fail_reason
            for name in ("docs", "tests", "legacy", "research", "outputs"):
                probe = subprocess.run(
                    ["docker", "run", "--rm", IMAGE_REPO, "sh", "-lc", f"test ! -e /app/{name}"],
                    cwd=REPO,
                    text=True,
                    capture_output=True,
                )
                absent_dirs[name] = probe.returncode == 0
    finally:
        logs = subprocess.run(["docker", "logs", CONTAINER_NAME], cwd=REPO, text=True, capture_output=True)
        logs_tail = (logs.stdout + logs.stderr)[-4000:]
        _docker_rm(CONTAINER_NAME)

    _run(["docker", "save", IMAGE_REPO, "-o", str(tar_path)], capture=True)
    tar_sha = _sha256_file(tar_path)

    verify = {
        "system_version": VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "image_tag": IMAGE_REPO,
        "image_id": image_id,
        "docker_run_container_id": run.stdout.strip(),
        "health_ok": health_ok,
        "health_note": health_note,
        "version_payload": version_payload,
        "analyze_ok": analyze_ok,
        "analyze_note": analyze_note,
        "fail_reason": fail_reason,
        "analyze_keys": list(analyze_payload.keys())[:24] if isinstance(analyze_payload, dict) else [],
        "forbidden_dirs_absent": absent_dirs,
        "tar_name": tar_path.name,
        "tar_sha256": tar_sha,
        "logs_tail": logs_tail,
    }
    verify_path.write_text(json.dumps(verify, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest = {
        "system_version": VERSION,
        "bundle_kind": "docker_shipping_bundle",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "image_tag": IMAGE_REPO,
        "dockerfile": "Dockerfile.shipping",
        "requirements_file": "requirements/shipping.txt",
        "tarball": tar_path.name,
        "tar_sha256": tar_sha,
        "verification_file": VERIFY_NAME,
        "note_file": BUILD_NOTE_NAME,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ok = (
        health_ok
        and analyze_ok
        and version_payload.get("version") == VERSION
        and all(absent_dirs.values())
    )
    print(json.dumps(verify, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
