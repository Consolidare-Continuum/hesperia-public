import React, { useCallback, useEffect, useRef, useState } from "react";
import { SECTORS, BANDS, familyLinearIndex } from "../topology/spheroidLattice.js";
import { getFillColor } from "../render/modes.js";

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

/**
 * @param {import('../schema/hexSchema.js').HexState[]} cells
 * @param {import('../render/modes.js').RenderMode} renderMode
 */
export default function FamilyLatticeFlatCanvas({ cells, renderMode, selectedId, hoveredId, search, onSelect, onHover }) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const dprRef = useRef(1);
  const draggingRef = useRef(false);
  const lastMouseRef = useRef({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const bySb = useCallback(() => {
    const m = new Map();
    for (const c of cells) {
      const s = c.sector ?? c.q;
      const b = c.band ?? c.r;
      m.set(`${s},${b}`, c);
    }
    return m;
  }, [cells]);

  useEffect(() => {
    const el = wrapRef.current;
    const canvas = canvasRef.current;
    if (!el || !canvas) return;
    function resize() {
      const r = el.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      dprRef.current = dpr;
      canvas.width = Math.floor(r.width * dpr);
      canvas.height = Math.floor(r.height * dpr);
      canvas.style.width = `${r.width}px`;
      canvas.style.height = `${r.height}px`;
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const el = wrapRef.current;
    if (!canvas || !el) return;
    const ctx = canvas.getContext("2d");
    const rect = el.getBoundingClientRect();
    const dpr = dprRef.current;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.scale(dpr, dpr);
    ctx.fillStyle = "#08111f";
    ctx.fillRect(0, 0, rect.width, rect.height);

    const pad = 28;
    const gw = rect.width - pad * 2;
    const gh = rect.height - pad * 2;
    const cw = gw / SECTORS;
    const ch = gh / BANDS;
    const map = bySb();

    function center(s, b) {
      return { cx: pad + (s + 0.5) * cw, cy: pad + (b + 0.5) * ch };
    }

    ctx.save();
    ctx.translate(rect.width / 2 + pan.x, rect.height / 2 + pan.y);
    ctx.scale(zoom, zoom);
    ctx.translate(-rect.width / 2, -rect.height / 2);

    ctx.strokeStyle = "rgba(255,255,255,0.16)";
    ctx.lineWidth = 1 / zoom;
    for (let b = 0; b < BANDS; b++) {
      for (let s = 0; s < SECTORS; s++) {
        const p0 = center(s, b);
        const pr = center((s + 1) % SECTORS, b);
        ctx.beginPath();
        ctx.moveTo(p0.cx, p0.cy);
        ctx.lineTo(pr.cx, pr.cy);
        ctx.stroke();
        if (b < BANDS - 1) {
          const pd = center(s, b + 1);
          ctx.beginPath();
          ctx.moveTo(p0.cx, p0.cy);
          ctx.lineTo(pd.cx, pd.cy);
          ctx.stroke();
        }
      }
    }
    ctx.setLineDash([4 / zoom, 4 / zoom]);
    ctx.strokeStyle = "rgba(250, 204, 21, 0.32)";
    for (let b = 0; b < BANDS; b++) {
      const a = center(11, b);
      const o = center(0, b);
      ctx.beginPath();
      ctx.moveTo(a.cx, a.cy);
      ctx.bezierCurveTo(a.cx + cw * 0.55, a.cy + ch * 0.75, o.cx - cw * 0.55, o.cy + ch * 0.75, o.cx, o.cy);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    if (renderMode === "boundary") {
      ctx.lineWidth = 1.3 / zoom;
      for (let b = 0; b < BANDS; b++) {
        for (let s = 0; s < SECTORS; s++) {
          const h = map.get(`${s},${b}`);
          if (!h) continue;
          const pr = map.get(`${(s + 1) % SECTORS},${b}`);
          if (pr && pr.dominant_area !== h.dominant_area) {
            const p0 = center(s, b);
            const p1 = center((s + 1) % SECTORS, b);
            ctx.beginPath();
            ctx.moveTo(p0.cx, p0.cy);
            ctx.lineTo(p1.cx, p1.cy);
            ctx.strokeStyle = "rgba(255,255,255,0.45)";
            ctx.stroke();
          }
          if (b < BANDS - 1) {
            const pd = map.get(`${s},${b + 1}`);
            if (pd && pd.dominant_area !== h.dominant_area) {
              const p0 = center(s, b);
              const p1 = center(s, b + 1);
              ctx.beginPath();
              ctx.moveTo(p0.cx, p0.cy);
              ctx.lineTo(p1.cx, p1.cy);
              ctx.strokeStyle = "rgba(255,255,255,0.45)";
              ctx.stroke();
            }
          }
        }
      }
    }

    const nodeR = Math.min(cw, ch) * 0.3;
    for (let b = 0; b < BANDS; b++) {
      for (let s = 0; s < SECTORS; s++) {
        const h = map.get(`${s},${b}`);
        if (!h) continue;
        const idx = familyLinearIndex(s, b);
        const { cx, cy } = center(s, b);
        ctx.beginPath();
        ctx.arc(cx, cy, nodeR, 0, Math.PI * 2);
        ctx.fillStyle = getFillColor(h, renderMode, idx);
        ctx.fill();
        if (h.id === selectedId || h.id === hoveredId) {
          ctx.lineWidth = h.id === selectedId ? 2.4 / zoom : 1.6 / zoom;
          ctx.strokeStyle = "rgba(255,255,255,0.92)";
          ctx.stroke();
        }
        if (search.trim()) {
          const needle = search.trim().toLowerCase();
          const hit =
            h.id.toLowerCase().includes(needle) ||
            String(h.family_id).includes(needle) ||
            `s${s}b${b}`.includes(needle) ||
            String(h.dominant_area).includes(needle);
          if (hit) {
            ctx.beginPath();
            ctx.arc(cx, cy, nodeR + 4 / zoom, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(255,255,255,0.7)";
            ctx.lineWidth = 1.1 / zoom;
            ctx.stroke();
          }
        }
      }
    }

    ctx.restore();

    ctx.fillStyle = "rgba(226,232,240,0.75)";
    ctx.font = "11px sans-serif";
    ctx.fillText("b=0 north", 8, 16);
    ctx.fillText("b=23 south", 8, rect.height - 8);
  }, [cells, renderMode, selectedId, hoveredId, search, zoom, pan, bySb]);

  function screenToLattice(clientX, clientY) {
    const el = wrapRef.current;
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const x = clientX - r.left;
    const y = clientY - r.top;
    const pad = 28;
    const gw = r.width - pad * 2;
    const gh = r.height - pad * 2;
    const lx = (x - r.width / 2 - pan.x) / zoom + r.width / 2;
    const ly = (y - r.height / 2 - pan.y) / zoom + r.height / 2;
    const s = Math.floor((lx - pad) / (gw / SECTORS));
    const b = Math.floor((ly - pad) / (gh / BANDS));
    if (s < 0 || s >= SECTORS || b < 0 || b >= BANDS) return null;
    return { s, b };
  }

  function handleMouseDown(e) {
    draggingRef.current = true;
    lastMouseRef.current = { x: e.clientX, y: e.clientY };
  }

  function handleMouseMove(e) {
    if (draggingRef.current) {
      const dx = e.clientX - lastMouseRef.current.x;
      const dy = e.clientY - lastMouseRef.current.y;
      lastMouseRef.current = { x: e.clientX, y: e.clientY };
      setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
      return;
    }
    const lb = screenToLattice(e.clientX, e.clientY);
    if (!lb) {
      onHover(null);
      return;
    }
    const c = cells.find((x) => (x.sector ?? x.q) === lb.s && (x.band ?? x.r) === lb.b);
    onHover(c ? c.id : null);
  }

  function handleMouseUp(e) {
    const moved = Math.abs(e.clientX - lastMouseRef.current.x) + Math.abs(e.clientY - lastMouseRef.current.y);
    draggingRef.current = false;
    if (moved < 4) {
      const lb = screenToLattice(e.clientX, e.clientY);
      if (!lb) {
        onSelect(null);
        return;
      }
      const c = cells.find((x) => (x.sector ?? x.q) === lb.s && (x.band ?? x.r) === lb.b);
      onSelect(c ? c.id : null);
    }
  }

  function handleWheel(e) {
    e.preventDefault();
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const mx = e.clientX - r.left;
    const my = e.clientY - r.top;
    const scale = e.deltaY < 0 ? 1.1 : 0.91;
    const next = clamp(zoom * scale, 0.4, 8);
    const wx = (mx - r.width / 2 - pan.x) / zoom;
    const wy = (my - r.height / 2 - pan.y) / zoom;
    setZoom(next);
    setPan({
      x: mx - r.width / 2 - wx * next,
      y: my - r.height / 2 - wy * next,
    });
  }

  return (
    <div className="relative w-full h-full" ref={wrapRef}>
      <canvas
        ref={canvasRef}
        className="absolute inset-0 cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          draggingRef.current = false;
          onHover(null);
        }}
        onWheel={handleWheel}
      />
    </div>
  );
}
