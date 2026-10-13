import json
from pathlib import Path

from django.test import Client, TestCase, override_settings


class OutputViewsSmokeTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_health(self) -> None:
        r = self.client.get("/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

    def test_operator_home(self) -> None:
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_client_preview(self) -> None:
        r = self.client.get("/preview/client/")
        self.assertEqual(r.status_code, 200)


class SessionInspectorMVPTests(TestCase):
    """T13–T21, T30 (partial), T54–T55 docs — fixture-backed inspector."""

    def test_inspector_200(self) -> None:
        r = self.client.get("/inspector/session_inspector_min/")
        self.assertEqual(r.status_code, 200)

    def test_pii_export_dialog_present(self) -> None:
        r = self.client.get("/inspector/session_inspector_min/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("pii-export-dialog", body)
        self.assertIn("Before you export", body)

    def test_inspector_dropdown_two_iterations(self) -> None:
        r = self.client.get("/inspector/session_inspector_min/")
        body = r.content.decode("utf-8")
        self.assertIn('value="0"', body)
        self.assertIn('value="1"', body)

    def test_deep_link_sentence_active(self) -> None:
        r = self.client.get("/inspector/session_inspector_min/?iteration=1&sentence=s1")
        self.assertEqual(r.status_code, 200)
        self.assertIn("is-active", r.content.decode("utf-8"))

    def test_unknown_bundle_404(self) -> None:
        r = self.client.get("/inspector/does_not_exist_fixture/")
        self.assertEqual(r.status_code, 404)

    def test_inspector_goldset_stem_fixture_200(self) -> None:
        """OUT-VIEW-FULL-02 — pipeline-shaped fixture `1-11-09-2023.json` loads."""
        r = self.client.get("/inspector/1-11-09-2023/")
        self.assertEqual(r.status_code, 200)

    def test_inspector_pipeline_fixture_shows_audit_planes(self) -> None:
        """OUT-VIEW-FULL-03 — Pane C surfaces audit.planes from pipeline bundle."""
        r = self.client.get("/inspector/1-11-09-2023/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("Pipeline planes", body)
        self.assertIn("01_structural_batch", body)

    def test_inspector_h070_pane2_gate_state(self) -> None:
        """H070-14..16 — Pane 2 gate state, diff/scores, rollback path."""
        r = self.client.get("/inspector/session_inspector_h070_apply/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("Pane 2", body)
        self.assertIn("applied", body)
        self.assertIn("Rollback artifact", body)
        self.assertIn("Evidence IDs", body)
        self.assertIn("Diff (deterministic hunks)", body)


class SessionInspectorExportTests(TestCase):
    """T22–T25 export.json + proxy gate."""

    def test_export_json_has_messages(self) -> None:
        r = self.client.get("/inspector/session_inspector_min/export.json?iteration=0")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("messages", data)
        self.assertGreaterEqual(len(data["messages"]), 2)
        disp = r.get("Content-Disposition", "")
        self.assertIn("attachment", disp)
        self.assertIn("segment.json", disp)

    @override_settings(HESPERIA_OUTPUT_VIEWS_OPENAI_PROXY=False)
    def test_openai_proxy_disabled_404(self) -> None:
        r = self.client.post("/inspector/session_inspector_min/openai-proxy/", {"iteration": "0"})
        self.assertEqual(r.status_code, 404)

    @override_settings(HESPERIA_OUTPUT_VIEWS_OPENAI_PROXY=True, OPENAI_API_KEY="")
    def test_openai_proxy_no_key_503(self) -> None:
        r = self.client.post("/inspector/session_inspector_min/openai-proxy/", {"iteration": "0"})
        self.assertEqual(r.status_code, 503)


class IterationSegmentOpenAiV1Tests(TestCase):
    """T04, T29, T63 — segment schema + messages contract."""

    def test_golden_fixture_extract_finalize_validate(self) -> None:
        from segment import (
            extract_iteration_segment,
            finalize_segment_openai_v1,
            validate_iteration_segment_openai_v1,
        )

        root = Path(__file__).resolve().parent.parent.parent
        raw = (root / "tests" / "fixtures" / "session_inspector_min.json").read_text(encoding="utf-8")
        bundle = json.loads(raw)
        base = extract_iteration_segment(bundle, "iter_0")
        final = finalize_segment_openai_v1(base)
        validate_iteration_segment_openai_v1(final)

    def test_t63_messages_roles(self) -> None:
        from segment import (
            extract_iteration_segment,
            finalize_segment_openai_v1,
        )

        root = Path(__file__).resolve().parent.parent.parent
        raw = (root / "tests" / "fixtures" / "session_inspector_min.json").read_text(encoding="utf-8")
        bundle = json.loads(raw)
        base = extract_iteration_segment(bundle, "iter_0")
        final = finalize_segment_openai_v1(base)
        msgs = final["messages"]
        self.assertGreaterEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertTrue(msgs[0]["content"].strip())
        self.assertTrue(msgs[1]["content"].strip())


class TfpPipelineBundleTests(TestCase):
    """T02 — engine bundle dir → session_inspector_v1."""

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]

    def test_build_from_ci_fixture_dir(self) -> None:
        from segment.tfp_pipeline_bundle import build_session_inspector_v1_from_tfp_pipeline_dir

        ci = self.repo_root / "tests" / "fixtures" / "tfp_calibration_bundle_ci"
        b = build_session_inspector_v1_from_tfp_pipeline_dir(ci, session_id="1-11-09-2023")
        self.assertEqual(b.get("schema_version"), "session_inspector_v1")
        meta = b.get("meta") or {}
        self.assertEqual(meta.get("source_label"), "1-11-09-2023")
        iters = b.get("iterations") or []
        self.assertEqual(len(iters), 1)
        it0 = iters[0]
        self.assertEqual(it0.get("order"), 0)
        self.assertEqual(it0.get("iteration_id"), "iter_0")
        params = it0.get("parameters") or {}
        self.assertIn("areas", params)
        mods = (params.get("modules") or {}).get("tfp.v1") or {}
        self.assertIn("structural_L1", mods)

    def test_write_fixture_roundtrip(self) -> None:
        import tempfile

        from segment.tfp_pipeline_bundle import write_session_inspector_fixture

        ci = self.repo_root / "tests" / "fixtures" / "tfp_calibration_bundle_ci"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.json"
            path = write_session_inspector_fixture(ci, p, session_id="1-11-09-2023")
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "session_inspector_v1")
