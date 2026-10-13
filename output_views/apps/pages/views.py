from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from segment.validate import validate_iteration_segment_openai_v1

from . import inspector as insp
from . import h070_pane
from .inspector import _SESSION_ID_RE
from .openai_export import final_segment_for_bundle
from segment.constants import DISCLAIMER_FOOTER_EN

logger = logging.getLogger(__name__)


def _rate_allow_openai_proxy(ip: str, limit: int) -> bool:
    """Fixed 60s window per IP (LocMem cache)."""
    bucket = int(time.time()) // 60
    key = f"openai_proxy:{ip}:{bucket}"
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 70)
        n = 1
    return n <= limit


@require_GET
def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok", "surface": "hesperia_output_views"})


@require_GET
def operator_home(request: HttpRequest) -> HttpResponse:
    """Operator landing: links to preview surfaces and health."""
    return render(
        request,
        "pages/operator_home.html",
        {
            "title": "Hesperia output views",
            "hesperia_root": settings.HESPERIA_ROOT,
        },
    )


@require_GET
def client_preview(request: HttpRequest) -> HttpResponse:
    """Client-centric placeholder page — static shell for future report builder."""
    return render(
        request,
        "pages/client_preview.html",
        {"title": "Client preview", "subtitle": "Hesperia structured outputs (HTML)"},
    )


@require_GET
def export_segment_json(request: HttpRequest, session_id: str) -> HttpResponse:
    """T23 — Download `iteration_segment_openai_v1` + messages as segment.json."""
    bundle = insp.load_inspector_fixture(session_id)
    try:
        order = int(request.GET.get("iteration", "0"))
    except ValueError:
        order = 0
    try:
        final = final_segment_for_bundle(bundle, order)
        validate_iteration_segment_openai_v1(final)
    except (KeyError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)
    resp = JsonResponse(final, json_dumps_params={"indent": 2, "ensure_ascii": False})
    resp["Content-Disposition"] = 'attachment; filename="segment.json"'
    return resp


@csrf_protect
@require_POST
def openai_proxy(request: HttpRequest, session_id: str) -> HttpResponse:
    """T24–T25 — Optional Chat Completions proxy; no request body logging in prod paths."""
    if not getattr(settings, "HESPERIA_OUTPUT_VIEWS_OPENAI_PROXY", False):
        return HttpResponseNotFound()
    api_key = (getattr(settings, "OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        return JsonResponse({"error": "OPENAI_API_KEY not configured"}, status=503)

    ip = request.META.get("REMOTE_ADDR", "unknown")
    lim = int(getattr(settings, "OPENAI_PROXY_RATE_PER_MINUTE", 30))
    if not _rate_allow_openai_proxy(ip, lim):
        return JsonResponse({"error": "rate limit"}, status=429)

    try:
        order = int(request.POST.get("iteration", "0"))
    except ValueError:
        return JsonResponse({"error": "bad iteration"}, status=400)

    bundle = insp.load_inspector_fixture(session_id)
    try:
        final = final_segment_for_bundle(bundle, order)
        messages = final.get("messages") or []
    except (KeyError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)

    model = getattr(settings, "OPENAI_PROXY_MODEL", "gpt-4o-mini")
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        ms = int((time.perf_counter() - t0) * 1000)
        logger.warning("openai_proxy http_error status=%s ms=%s", getattr(e, "code", "?"), ms)
        return JsonResponse({"error": "upstream", "status": getattr(e, "code", None)}, status=502)
    except OSError as e:
        ms = int((time.perf_counter() - t0) * 1000)
        logger.warning("openai_proxy transport ms=%s err=%s", ms, type(e).__name__)
        return JsonResponse({"error": "transport"}, status=502)

    ms = int((time.perf_counter() - t0) * 1000)
    logger.info("openai_proxy ok model=%s ms=%s", model, ms)
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = ""
    return JsonResponse({"ok": True, "content": content})


@require_GET
def session_inspector(request: HttpRequest, session_id: str) -> HttpResponse:
    """T13–T21 — Session Inspector MVP (fixture-backed). Deep links: ?iteration=&sentence="""
    bundle = insp.load_inspector_fixture(session_id)
    meta = bundle.get("meta") or {}
    order_q = request.GET.get("iteration")
    current, all_iter = insp.resolve_iteration(bundle, order_q)
    sentences = insp.sourced_text_lines(current)
    sentence_q = request.GET.get("sentence")
    if sentence_q:
        active_sid = sentence_q.strip()
    elif sentences:
        active_sid = str(sentences[0].get("id", ""))
    else:
        active_sid = ""

    iter_options: list[dict[str, str | int]] = []
    for it in all_iter:
        iter_options.append(
            {
                "order": int(it.get("order", 0)),
                "iteration_id": str(it.get("iteration_id", "")),
                "label": insp.iteration_label(it),
            }
        )

    params = current.get("parameters") or {}
    areas = params.get("areas") if isinstance(params.get("areas"), dict) else {}
    families = params.get("families") if isinstance(params.get("families"), dict) else {}
    metrics = params.get("metrics") if isinstance(params.get("metrics"), dict) else {}
    modules = params.get("modules") if isinstance(params.get("modules"), dict) else {}
    modules_json = mark_safe(json.dumps(modules, indent=2, ensure_ascii=False)) if modules else ""
    tfp_profile = params.get("tfp_profile") if isinstance(params.get("tfp_profile"), dict) else {}
    if not tfp_profile:
        ext = ((modules.get("tfp") or {}).get("v1") or {}).get("analyze_extended") or {}
        if isinstance(ext, dict):
            tfp_profile = {
                "grain": ext.get("grain"),
                "pack": ext.get("pack"),
                "dict_mode": ext.get("dict_mode"),
                "structure": ext.get("structure"),
            }
    # also from bundle meta.analyze_profile
    apm = meta.get("analyze_profile") if isinstance(meta.get("analyze_profile"), dict) else {}
    tfp_grain = tfp_profile.get("grain") or apm.get("area_math") or apm.get("grain")
    tfp_pack = tfp_profile.get("pack") or apm.get("pack_areas") or apm.get("pack")
    tfp_dict_mode = tfp_profile.get("dict_mode") or apm.get("dict_mode")
    tfp_structure = tfp_profile.get("structure") or apm.get("structure_map") or apm.get("structure")

    audit = current.get("audit") if isinstance(current.get("audit"), dict) else {}
    audit_iteration = audit.get("iteration") if isinstance(audit.get("iteration"), dict) else {}
    audit_planes = audit.get("planes") if isinstance(audit.get("planes"), dict) else {}
    audit_by_sentence = audit.get("by_sentence") if isinstance(audit.get("by_sentence"), dict) else {}
    has_audit_planes_or_iteration = bool(audit_planes or audit_iteration)
    has_sentence_audit = bool(audit_by_sentence)
    audit_planes_json = mark_safe(json.dumps(audit_planes, indent=2, ensure_ascii=False)) if audit_planes else ""
    audit_iteration_json = mark_safe(json.dumps(audit_iteration, indent=2, ensure_ascii=False)) if audit_iteration else ""

    # Relations strip — top areas by weight (no recompute; display-only summary)
    relations_summary: list[str] = []
    if isinstance(areas, dict) and areas:
        top = sorted(areas.items(), key=lambda x: float(x[1] or 0), reverse=True)[:5]
        relations_summary.append(
            "Top areas (by scalar): " + ", ".join(f"{k} ({float(v):.4f})" for k, v in top if v is not None)
        )
    if isinstance(families, dict) and families:
        ft = sorted(families.items(), key=lambda x: float(x[1] or 0), reverse=True)[:5]
        relations_summary.append(
            "Families: " + ", ".join(f"{k} ({float(v):.4f})" for k, v in ft if v is not None)
        )

    try:
        export_segment = final_segment_for_bundle(bundle, int(current.get("order", 0)))
        validate_iteration_segment_openai_v1(export_segment)
    except (KeyError, ValueError, TypeError, OSError, FileNotFoundError) as e:
        logger.debug("export_segment unavailable session=%s err=%s", session_id, e)
        export_segment = None

    pane2 = h070_pane.pane2_from_iteration(current)
    if pane2:
        pane2 = dict(pane2)
        pane2["diff_json"] = mark_safe(json.dumps(pane2.get("diff_hunks"), indent=2, ensure_ascii=False))
        pane2["scores_json"] = mark_safe(json.dumps(pane2.get("scores"), indent=2, ensure_ascii=False))

    return render(
        request,
        "pages/session_inspector.html",
        {
            "title": "Session Inspector",
            "session_id": session_id,
            "meta": meta,
            "bundle": bundle,
            "iterations": iter_options,
            "current": current,
            "current_order": int(current.get("order", 0)),
            "sentences": sentences,
            "active_sentence_id": active_sid,
            "parameters": params,
            "parameters_json": mark_safe(json.dumps(params, indent=2, ensure_ascii=False)),
            "areas": areas,
            "families": families,
            "metrics": metrics,
            "modules": modules,
            "modules_json": modules_json,
            "tfp_grain": tfp_grain,
            "tfp_pack": tfp_pack,
            "tfp_dict_mode": tfp_dict_mode,
            "tfp_structure": tfp_structure,
            "audit": audit,
            "audit_iteration": audit_iteration,
            "audit_planes": audit_planes,
            "audit_by_sentence": audit_by_sentence,
            "audit_planes_json": audit_planes_json,
            "audit_iteration_json": audit_iteration_json,
            "has_audit_planes_or_iteration": has_audit_planes_or_iteration,
            "has_sentence_audit": has_sentence_audit,
            "relations_summary": relations_summary,
            "disclaimer": meta.get("disclaimer_footer") or DISCLAIMER_FOOTER_EN,
            "export_segment": export_segment,
            "openai_proxy_enabled": getattr(settings, "HESPERIA_OUTPUT_VIEWS_OPENAI_PROXY", False),
            "pane2": pane2,
        },
    )


@require_GET
def sessions_index(request: HttpRequest) -> HttpResponse:
    """List available session fixtures (read-only; no path injection)."""
    root = Path(settings.BASE_DIR) / "tests" / "fixtures"
    sessions: list[str] = []
    if root.is_dir():
        sessions = sorted(
            p.stem
            for p in root.iterdir()
            if p.is_file() and p.suffix == ".json" and _SESSION_ID_RE.match(p.stem)
        )
    return render(
        request,
        "pages/sessions_index.html",
        {"title": "Sessions", "sessions": sessions},
    )


@require_GET
def artifact_sample(request: HttpRequest) -> HttpResponse:
    """Read-only sample: list e2e artifact filenames (no path injection)."""
    root = Path(settings.HESPERIA_ROOT) / "assets" / "artifacts" / "e2e"
    names: list[str] = []
    if root.is_dir():
        names = sorted(p.name for p in root.iterdir() if p.is_file() and p.suffix == ".json")[:50]
    return render(
        request,
        "pages/artifact_list.html",
        {"title": "E2E artifacts (sample)", "artifacts": names, "root_display": str(root)},
    )
