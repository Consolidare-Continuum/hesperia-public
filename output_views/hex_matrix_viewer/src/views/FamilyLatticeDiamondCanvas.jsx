import React, { useCallback, useEffect, useRef, useState } from "react";
import { SECTORS, BANDS, familyLinearIndex } from "../topology/spheroidLattice.js";
import { getFillColor } from "../render/modes.js";

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

/** Diamond view only: softer saturation / lift lightness (no topology change). */
function softenFillForDiamond(css) {
  const t = css.trim();
  const hsl = /^hsl\(\s*([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\s*\)/i.exec(t);
  if (hsl) {
    const sat = Math.min(100, parseFloat(hsl[2]) * 0.8);
    const light = Math.min(100, parseFloat(hsl[3]) * 1.05);
    return `hsl(${hsl[1]} ${sat}% ${light}%)`;
  }
  const rgba = /^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)/i.exec(t);
  if (rgba) {
    const r = Math.min(255, +rgba[1] * 0.96 + 10);
    const g = Math.min(255, +rgba[2] * 0.96 + 10);
    const b = Math.min(255, +rgba[3] * 0.96 + 10);
    const a = Math.min(1, parseFloat(rgba[4]) * 1.05);
    return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${a})`;
  }
  const rgb = /^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i.exec(t);
  if (rgb) {
    const mix = (x) => Math.min(255, x * 0.92 + 18);
    return `rgb(${Math.round(mix(+rgb[1]))}, ${Math.round(mix(+rgb[2]))}, ${Math.round(mix(+rgb[3]))})`;
  }
  return t;
}

/** Rhomb edge / band: weaker at poles, stronger at equator (b 0..23). */
function diamondEdgeFadeAtRow(bRow) {
  const t = Math.abs(bRow - 11.5) / 11.5;
  return 1 - 0.5 * t;
}

/**
 * Band-centered diamond: inspection / cognition layout (not 3D truth). 288 cells F(s,b).
 */
export default function FamilyLatticeDiamondCanvas({ cells, renderMode, selectedId, hoveredId, search, onSelect, onHover }) {
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

  /** Evenly spread 12 sectors across row; center-aligned, no collisions. */
  function diamondCenter(s, b, rect, pad, gw, gh) {
    const width = 1 + Math.min(b, BANDS - 1 - b);
    const xNorm = (s + 0.5) * (width / 12) - width / 2;
    const centerX = rect.width / 2;
    const rowInner = (width / 12) * gw;
    const cx = centerX + xNorm * (rowInner / width);
    const ch = gh / BANDS;
    const cy = pad + (b + 0.5) * ch;
    const cellPitch = rowInner / 12;
    return { cx, cy, cellPitch, ch, width };
  }

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
    const map = bySb();

    ctx.save();
    ctx.translate(rect.width / 2 + pan.x, rect.height / 2 + pan.y);
    ctx.scale(zoom, zoom);
    ctx.translate(-rect.width / 2, -rect.height / 2);

    ctx.lineWidth = 1 / zoom;
    for (let b = 0; b < BANDS; b++) {
      const fade = diamondEdgeFadeAtRow(b);
      ctx.strokeStyle = `rgba(255,255,255,${0.08 * fade})`;
      const y = pad + (b + 0.5) * (gh / BANDS);
      ctx.beginPath();
      ctx.moveTo(pad, y);
      ctx.lineTo(rect.width - pad, y);
      ctx.stroke();
    }

    ctx.lineWidth = 1 / zoom;
    const rhombBaseA = 0.32;
    for (let b = 0; b < BANDS - 1; b++) {
      for (let s = 0; s < SECTORS - 1; s++) {
        const fade = diamondEdgeFadeAtRow(b + 0.5);
        const a = rhombBaseA * fade;
        if ((s + b) % 2 === 0) {
          const p0 = diamondCenter(s, b, rect, pad, gw, gh);
          const p1 = diamondCenter(s + 1, b + 1, rect, pad, gw, gh);
          ctx.strokeStyle = `rgba(148,163,184,${a})`;
          ctx.beginPath();
          ctx.moveTo(p0.cx, p0.cy);
          ctx.lineTo(p1.cx, p1.cy);
          ctx.stroke();
        } else {
          const p0 = diamondCenter(s + 1, b, rect, pad, gw, gh);
          const p1 = diamondCenter(s, b + 1, rect, pad, gw, gh);
          ctx.strokeStyle = `rgba(148,163,184,${a})`;
          ctx.beginPath();
          ctx.moveTo(p0.cx, p0.cy);
          ctx.lineTo(p1.cx, p1.cy);
          ctx.stroke();
        }
      }
    }

    if (renderMode === "boundary") {
      ctx.lineWidth = 1.6 / zoom;
      const boundaryBaseA = 0.55;
      for (let b = 0; b < BANDS - 1; b++) {
        for (let s = 0; s < SECTORS - 1; s++) {
          const fade = diamondEdgeFadeAtRow(b + 0.5);
          const ba = boundaryBaseA * fade;
          if ((s + b) % 2 === 0) {
            const h00 = map.get(`${s},${b}`);
            const h11 = map.get(`${s + 1},${b + 1}`);
            if (h00 && h11 && h00.dominant_area !== h11.dominant_area) {
              const p0 = diamondCenter(s, b, rect, pad, gw, gh);
              const p1 = diamondCenter(s + 1, b + 1, rect, pad, gw, gh);
              ctx.strokeStyle = `rgba(250,250,250,${ba})`;
              ctx.beginPath();
              ctx.moveTo(p0.cx, p0.cy);
              ctx.lineTo(p1.cx, p1.cy);
              ctx.stroke();
            }
          } else {
            const h10 = map.get(`${s + 1},${b}`);
            const h01 = map.get(`${s},${b + 1}`);
            if (h10 && h01 && h10.dominant_area !== h01.dominant_area) {
              const p0 = diamondCenter(s + 1, b, rect, pad, gw, gh);
              const p1 = diamondCenter(s, b + 1, rect, pad, gw, gh);
              ctx.strokeStyle = `rgba(250,250,250,${ba})`;
              ctx.beginPath();
              ctx.moveTo(p0.cx, p0.cy);
              ctx.lineTo(p1.cx, p1.cy);
              ctx.stroke();
            }
          }
        }
      }
    }

    for (let b = 0; b < BANDS; b++) {
      for (let s = 0; s < SECTORS; s++) {
        const h = map.get(`${s},${b}`);
        if (!h) continue;
        const idx = familyLinearIndex(s, b);
        const pos = diamondCenter(s, b, rect, pad, gw, gh);
        const equator = b === 11 || b === 12;
        const silhouette = b === 0 || b === BANDS - 1 || s === 0 || s === SECTORS - 1;
        const baseR = Math.min(pos.cellPitch, pos.ch) * 0.28 * 0.7;
        const nodeR = baseR * (equator ? 1.15 : 1) * (silhouette ? 1.2 : 1);
        ctx.save();
        ctx.globalAlpha = equator || silhouette ? 1 : 0.85;
        ctx.beginPath();
        ctx.arc(pos.cx, pos.cy, nodeR, 0, Math.PI * 2);
        ctx.fillStyle = softenFillForDiamond(getFillColor(h, renderMode, idx));
        ctx.fill();
        ctx.restore();
        if (h.id === selectedId || h.id === hoveredId) {
          ctx.lineWidth = h.id === selectedId ? 2.4 / zoom : 1.6 / zoom;
          ctx.strokeStyle = "rgba(255,255,255,0.92)";
          ctx.beginPath();
          ctx.arc(pos.cx, pos.cy, nodeR, 0, Math.PI * 2);
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
            ctx.arc(pos.cx, pos.cy, nodeR + 4 / zoom, 0, Math.PI * 2);
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
    ctx.fillText("Diamond · b=0 north", 8, 16);
    ctx.fillText("b=23 south", 8, rect.height - 8);
  }, [cells, renderMode, selectedId, hoveredId, search, zoom, pan, bySb]);

  function worldFromClient(clientX, clientY) {
    const el = wrapRef.current;
    if (!el) return { lx: 0, ly: 0 };
    const r = el.getBoundingClientRect();
    const x = clientX - r.left;
    const y = clientY - r.top;
    return {
      lx: (x - r.width / 2 - pan.x) / zoom + r.width / 2,
      ly: (y - r.height / 2 - pan.y) / zoom + r.height / 2,
    };
  }

  function hitDiamond(clientX, clientY) {
    const el = wrapRef.current;
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const pad = 28;
    const gw = r.width - pad * 2;
    const gh = r.height - pad * 2;
    const { lx, ly } = worldFromClient(clientX, clientY);
    let best = null;
    let bestD = 1e9;
    for (let b = 0; b < BANDS; b++) {
      for (let s = 0; s < SECTORS; s++) {
        const pos = diamondCenter(s, b, r, pad, gw, gh);
        const equator = b === 11 || b === 12;
        const silhouette = b === 0 || b === BANDS - 1 || s === 0 || s === SECTORS - 1;
        const nodeR =
          Math.min(pos.cellPitch, pos.ch) * 0.28 * 0.7 * (equator ? 1.15 : 1) * (silhouette ? 1.2 : 1);
        const d = Math.hypot(lx - pos.cx, ly - pos.cy);
        if (d <= nodeR * 1.35 && d < bestD) {
          best = { s, b };
          bestD = d;
        }
      }
    }
    return best;
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
    const lb = hitDiamond(e.clientX, e.clientY);
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
      const lb = hitDiamond(e.clientX, e.clientY);
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
    const next = clamp(zoom * scale, 0.35, 8);
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
