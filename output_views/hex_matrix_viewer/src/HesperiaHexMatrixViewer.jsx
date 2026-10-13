import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Search, ZoomIn, ZoomOut, RotateCcw, Layers, Eye, Grid3X3, Play, Pause, Pin, Globe, Hexagon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Slider } from "./components/ui/slider";
import { Badge } from "./components/ui/badge";
import { Switch } from "./components/ui/switch";
import { N_AREAS } from "./schema/hexSchema.js";
import { buildCoordMap, AXIAL_DIRS } from "./render/neighbors.js";
import { coherenceAreaScoresPass, coherenceScalarPass } from "./render/coherence.js";
import { getFillColor } from "./render/modes.js";
import { generateMockDataset, attachFrameTransitions } from "./mock/generateMockDataset.js";
import { loadDataset } from "./data/datasetPipeline.js";
import { aggregateHexesToFamilyCells, attachFamilyLatticeTransitions } from "./data/aggregateFamilies.js";
import FamilyLatticeFlatCanvas from "./views/FamilyLatticeFlatCanvas.jsx";
import FamilyLatticeDiamondCanvas from "./views/FamilyLatticeDiamondCanvas.jsx";
import FamilyLatticeThreeView from "./views/FamilyLatticeThreeView.jsx";
import { RelationsPanel } from "./components/RelationsPanel.jsx";

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function hexToPixel(q, r, size) {
  const x = size * Math.sqrt(3) * (q + r / 2);
  const y = size * 1.5 * r;
  return { x, y };
}

function pointToHex(x, y, size) {
  const q = ((Math.sqrt(3) / 3) * x - (1 / 3) * y) / size;
  const r = ((2 / 3) * y) / size;
  return hexRound(q, r);
}

function hexRound(q, r) {
  let x = q;
  let z = r;
  let y = -x - z;

  let rx = Math.round(x);
  let ry = Math.round(y);
  let rz = Math.round(z);

  const xDiff = Math.abs(rx - x);
  const yDiff = Math.abs(ry - y);
  const zDiff = Math.abs(rz - z);

  if (xDiff > yDiff && xDiff > zDiff) {
    rx = -ry - rz;
  } else if (yDiff > zDiff) {
    ry = -rx - rz;
  } else {
    rz = -rx - ry;
  }

  return { q: rx, r: rz };
}

function polygonPoints(cx, cy, size) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const angle = ((60 * i - 30) * Math.PI) / 180;
    pts.push({ x: cx + size * Math.cos(angle), y: cy + size * Math.sin(angle) });
  }
  return pts;
}

function fitBounds(hexes, size) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const h of hexes) {
    const { x, y } = hexToPixel(h.q, h.r, size);
    minX = Math.min(minX, x - size);
    minY = Math.min(minY, y - size);
    maxX = Math.max(maxX, x + size);
    maxY = Math.max(maxY, y + size);
  }

  return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
}

function readDataUrlParam() {
  if (typeof window === "undefined") return null;
  const u = new URLSearchParams(window.location.search).get("data");
  return u && u.trim() ? u.trim() : null;
}

function readDebugParam() {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("debug") === "1";
}

/** @typedef {import('./render/modes.js').RenderMode} RenderMode */

const MODE_OPTIONS = /** @type {const} */ ([
  { value: "dominant_area", label: "Dominant area (default)" },
  { value: "dominance_heat", label: "Dominance heat" },
  { value: "stability_heat", label: "Stability heat" },
  { value: "delta", label: "Delta (vs previous frame)" },
  { value: "boundary", label: "Contradiction / boundary" },
  { value: "family_layout", label: "Family layout inspect" },
]);

export default function HesperiaHexMatrixViewer() {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const dprRef = useRef(1);
  const draggingRef = useRef(false);
  const lastMouseRef = useRef({ x: 0, y: 0 });

  const [dataset, setDataset] = useState(() => generateMockDataset());
  const [dataError, setDataError] = useState(null);
  const [debugParam] = useState(() => readDebugParam());

  useEffect(() => {
    const url = readDataUrlParam();
    if (!url) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(url, { credentials: "omit" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          const loaded = loadDataset(json);
          attachFrameTransitions(loaded.frames);
          setDataset(loaded);
          setDataError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setDataError(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const [frameIndex, setFrameIndex] = useState(0);
  const [zoom, setZoom] = useState(0.12);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [hoveredId, setHoveredId] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  /** @type {[RenderMode, function]} */
  const [renderMode, setRenderMode] = useState(/** @type {RenderMode} */ ("dominant_area"));
  const [showGridStroke, setShowGridStroke] = useState(false);
  const [showLabels, setShowLabels] = useState(false);
  const [search, setSearch] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [hexSize, setHexSize] = useState(7);
  const [playbackMs, setPlaybackMs] = useState(220);
  const [coherenceOn, setCoherenceOn] = useState(false);
  const [coherenceKind, setCoherenceKind] = useState(/** @type {'area_scores' | 'dominance' | 'stability'} */ ("area_scores"));
  const [pinSelection, setPinSelection] = useState(true);
  /** @type {['lattice288' | 'hex72000', function]} */
  const [surfaceMode, setSurfaceMode] = useState(/** @type {'lattice288' | 'hex72000'} */ ("lattice288"));
  /** @type {['flat' | 'cylinder' | 'spheroid', function]} */
  const [projection, setProjection] = useState(/** @type {'flat' | 'diamond' | 'cylinder' | 'spheroid'} */ ("flat"));
  const [mergePoles, setMergePoles] = useState(true);

  const frameCount = dataset.frames.length;
  const currentFrame = dataset.frames[Math.min(frameIndex, frameCount - 1)];
  const rawHexes = currentFrame.hexes;

  const coherentFramesHexes = useMemo(() => {
    return dataset.frames.map((fr) => {
      let hx = fr.hexes;
      if (!coherenceOn) return hx;
      if (coherenceKind === "area_scores") return coherenceAreaScoresPass(hx);
      if (coherenceKind === "dominance") return coherenceScalarPass(hx, "dominance");
      return coherenceScalarPass(hx, "stability");
    });
  }, [dataset, coherenceOn, coherenceKind]);

  const displayHexes = coherentFramesHexes[Math.min(frameIndex, frameCount - 1)];

  const familyLatticeFrames = useMemo(() => {
    const agg = coherentFramesHexes.map((hx) => aggregateHexesToFamilyCells(hx));
    attachFamilyLatticeTransitions(agg);
    return agg;
  }, [coherentFramesHexes]);

  const displayFamilyCells = familyLatticeFrames[Math.min(frameIndex, frameCount - 1)];

  const coordMap = useMemo(() => buildCoordMap(displayHexes), [displayHexes]);

  const hexByCoord = useMemo(() => {
    const m = new Map();
    for (const h of displayHexes) {
      m.set(`${h.q},${h.r}`, h);
    }
    return m;
  }, [displayHexes]);

  const selectedHex = useMemo(() => {
    if (!selectedId) return null;
    if (surfaceMode === "lattice288") return displayFamilyCells.find((h) => h.id === selectedId) || null;
    return displayHexes.find((h) => h.id === selectedId) || null;
  }, [surfaceMode, displayFamilyCells, displayHexes, selectedId]);

  const rawSelectedHex = useMemo(() => {
    if (!selectedId || surfaceMode === "lattice288") return null;
    return rawHexes.find((h) => h.id === selectedId) || null;
  }, [rawHexes, selectedId, surfaceMode]);

  const hoveredHex = useMemo(() => {
    if (!hoveredId) return null;
    if (surfaceMode === "lattice288") return displayFamilyCells.find((h) => h.id === hoveredId) || null;
    return displayHexes.find((h) => h.id === hoveredId) || null;
  }, [surfaceMode, displayFamilyCells, displayHexes, hoveredId]);

  const prevFrameHexForSelected = useMemo(() => {
    if (!selectedId || frameIndex <= 0) return null;
    if (surfaceMode === "lattice288") {
      const prev = familyLatticeFrames[frameIndex - 1];
      return prev ? prev.find((h) => h.id === selectedId) || null : null;
    }
    const prev = dataset.frames[frameIndex - 1]?.hexes;
    if (!prev) return null;
    return prev.find((h) => h.id === selectedId) || null;
  }, [surfaceMode, familyLatticeFrames, dataset.frames, frameIndex, selectedId]);

  useEffect(() => {
    if (!isPlaying) return;
    const id = setInterval(() => {
      setFrameIndex((v) => (v + 1) % frameCount);
    }, playbackMs);
    return () => clearInterval(id);
  }, [isPlaying, frameCount, playbackMs]);

  useEffect(() => {
    if (!pinSelection) setSelectedId(null);
  }, [frameIndex, pinSelection]);

  useEffect(() => {
    setSelectedId(null);
  }, [surfaceMode]);

  useEffect(() => {
    if (surfaceMode !== "hex72000") return;
    const el = wrapRef.current;
    const canvas = canvasRef.current;
    if (!el || !canvas) return;

    function resize() {
      const rect = el.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      dprRef.current = dpr;
      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
    }

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(el);
    return () => observer.disconnect();
  }, [surfaceMode]);

  useEffect(() => {
    if (surfaceMode !== "hex72000") return;
    const el = wrapRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const bounds = fitBounds(displayHexes, hexSize);
    const scaleX = rect.width / Math.max(bounds.width, 1);
    const scaleY = rect.height / Math.max(bounds.height, 1);
    const initialZoom = Math.min(scaleX, scaleY) * 0.92;
    setZoom(initialZoom);
    setOffset({
      x: rect.width / 2 - (bounds.minX + bounds.width / 2) * initialZoom,
      y: rect.height / 2 - (bounds.minY + bounds.height / 2) * initialZoom,
    });
  }, [hexSize, surfaceMode, displayHexes]);

  useEffect(() => {
    if (surfaceMode !== "hex72000") return;
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

    const viewLeft = (-offset.x) / zoom - hexSize * 4;
    const viewTop = (-offset.y) / zoom - hexSize * 4;
    const viewRight = (rect.width - offset.x) / zoom + hexSize * 4;
    const viewBottom = (rect.height - offset.y) / zoom + hexSize * 4;

    const shouldDrawLabels = showLabels && zoom > 1.8;

    for (let hi = 0; hi < displayHexes.length; hi++) {
      const h = displayHexes[hi];
      const p = hexToPixel(h.q, h.r, hexSize);
      if (p.x < viewLeft || p.x > viewRight || p.y < viewTop || p.y > viewBottom) continue;

      const sx = p.x * zoom + offset.x;
      const sy = p.y * zoom + offset.y;
      const radius = hexSize * zoom;
      if (sx < -radius * 2 || sx > rect.width + radius * 2 || sy < -radius * 2 || sy > rect.height + radius * 2) continue;

      const pts = polygonPoints(sx, sy, radius);
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.closePath();
      ctx.fillStyle = getFillColor(h, renderMode, hi);
      ctx.fill();

      if (renderMode === "boundary") {
        for (let ei = 0; ei < 6; ei++) {
          const d = AXIAL_DIRS[ei];
          const nk = `${h.q + d.q},${h.r + d.r}`;
          const nh = coordMap.get(nk);
          if (!nh || nh.dominant_area !== h.dominant_area) {
            ctx.beginPath();
            ctx.moveTo(pts[ei].x, pts[ei].y);
            ctx.lineTo(pts[(ei + 1) % 6].x, pts[(ei + 1) % 6].y);
            ctx.strokeStyle = "rgba(255,255,255,0.78)";
            ctx.lineWidth = 1.1;
            ctx.stroke();
          }
        }
      }

      if (showGridStroke || h.id === hoveredId || h.id === selectedId) {
        ctx.lineWidth = h.id === selectedId ? 2.2 : h.id === hoveredId ? 1.6 : 0.5;
        ctx.strokeStyle = h.id === selectedId ? "rgba(255,255,255,0.95)" : h.id === hoveredId ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.12)";
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.closePath();
        ctx.stroke();
      }

      if (shouldDrawLabels) {
        ctx.fillStyle = "rgba(255,255,255,0.8)";
        ctx.font = `${Math.max(9, radius * 0.48)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(h.family_id), sx, sy);
      }
    }

    if (search.trim()) {
      const needle = search.trim().toLowerCase();
      const found = displayHexes.filter(
        (h) =>
          h.id.toLowerCase().includes(needle) ||
          String(h.family_id).toLowerCase().includes(needle) ||
          String(h.area_id).toLowerCase().includes(needle) ||
          String(h.dominant_area).includes(needle)
      );
      for (const h of found.slice(0, 250)) {
        const p = hexToPixel(h.q, h.r, hexSize);
        const sx = p.x * zoom + offset.x;
        const sy = p.y * zoom + offset.y;
        const radius = hexSize * zoom;
        ctx.beginPath();
        ctx.arc(sx, sy, Math.max(4, radius * 0.45), 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255,255,255,0.85)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
  }, [surfaceMode, displayHexes, zoom, offset, hoveredId, selectedId, renderMode, showGridStroke, showLabels, search, hexSize, coordMap]);

  function screenToWorld(clientX, clientY) {
    const rect = wrapRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return {
      x: (x - offset.x) / zoom,
      y: (y - offset.y) / zoom,
    };
  }

  function hitTest(clientX, clientY) {
    const { x, y } = screenToWorld(clientX, clientY);
    const h = pointToHex(x, y, hexSize);
    return hexByCoord.get(`${h.q},${h.r}`) || null;
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
      setOffset((o) => ({ x: o.x + dx, y: o.y + dy }));
      return;
    }

    const h = hitTest(e.clientX, e.clientY);
    setHoveredId(h ? h.id : null);
  }

  function handleMouseUp(e) {
    const moved = Math.abs(e.clientX - lastMouseRef.current.x) + Math.abs(e.clientY - lastMouseRef.current.y);
    draggingRef.current = false;
    if (moved < 4) {
      const h = hitTest(e.clientX, e.clientY);
      setSelectedId(h ? h.id : null);
    }
  }

  function handleWheel(e) {
    e.preventDefault();
    const rect = wrapRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const scale = e.deltaY < 0 ? 1.12 : 0.9;
    const nextZoom = clamp(zoom * scale, 0.03, 8);
    const wx = (mx - offset.x) / zoom;
    const wy = (my - offset.y) / zoom;
    setZoom(nextZoom);
    setOffset({
      x: mx - wx * nextZoom,
      y: my - wy * nextZoom,
    });
  }

  function resetView() {
    const el = wrapRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const bounds = fitBounds(displayHexes, hexSize);
    const scaleX = rect.width / Math.max(bounds.width, 1);
    const scaleY = rect.height / Math.max(bounds.height, 1);
    const initialZoom = Math.min(scaleX, scaleY) * 0.92;
    setZoom(initialZoom);
    setOffset({
      x: rect.width / 2 - (bounds.minX + bounds.width / 2) * initialZoom,
      y: rect.height / 2 - (bounds.minY + bounds.height / 2) * initialZoom,
    });
  }

  function zoomBy(factor) {
    const el = wrapRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const nextZoom = clamp(zoom * factor, 0.03, 8);
    const wx = (cx - offset.x) / zoom;
    const wy = (cy - offset.y) / zoom;
    setZoom(nextZoom);
    setOffset({ x: cx - wx * nextZoom, y: cy - wy * nextZoom });
  }

  function focusHexBySearch() {
    const needle = search.trim().toLowerCase();
    if (!needle) return;
    const pool = surfaceMode === "lattice288" ? displayFamilyCells : displayHexes;
    const found = pool.find(
      (h) =>
        h.id.toLowerCase().includes(needle) ||
        String(h.family_id).toLowerCase().includes(needle) ||
        String(h.area_id).toLowerCase().includes(needle) ||
        String(h.dominant_area) === needle ||
        (h.sector != null && `s${h.sector}`.includes(needle)) ||
        (h.band != null && `b${h.band}`.includes(needle))
    );
    if (!found || !wrapRef.current) return;
    if (surfaceMode === "hex72000") {
      const rect = wrapRef.current.getBoundingClientRect();
      const p = hexToPixel(found.q, found.r, hexSize);
      const nextZoom = Math.max(zoom, 1.3);
      setZoom(nextZoom);
      setOffset({
        x: rect.width / 2 - p.x * nextZoom,
        y: rect.height / 2 - p.y * nextZoom,
      });
    }
    setSelectedId(found.id);
  }

  const infoHex = selectedHex || hoveredHex;
  const datasetRelations = dataset?.relations ?? null;
  const datasetAppearDisappear = dataset?.appear_disappear ?? null;
  const byArea = useMemo(() => {
    const out = new Map();
    for (let i = 0; i < N_AREAS; i++) out.set(i, 0);
    const src = surfaceMode === "lattice288" ? displayFamilyCells : displayHexes;
    for (const h of src) {
      const k = h.dominant_area;
      out.set(k, (out.get(k) || 0) + h.dominance);
    }
    return Array.from(out.entries()).sort((a, b) => b[1] - a[1]);
  }, [displayHexes, displayFamilyCells, surfaceMode]);

  const modeSelectOptions = useMemo(() => {
    const base = [...MODE_OPTIONS];
    if (debugParam) {
      base.push({ value: "family_spectrum_debug", label: "Family spectrum (debug — misleading)" });
    }
    return base;
  }, [debugParam]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      {dataError ? (
        <div className="mb-4 rounded-2xl border border-amber-700/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
          <span className="font-semibold">Data URL failed:</span> {dataError} (showing mock data until fixed)
        </div>
      ) : null}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-4"
      >
        <div className="space-y-4">
          <Card className="bg-slate-900/80 border-slate-800 rounded-2xl shadow-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <Grid3X3 className="w-5 h-5" />
                HESPERIA Hex Matrix
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-slate-300 leading-6">
                Truth: 12×24 sphere (288 families). Flat = debug grid; diamond = inspection layout; cylinder/sphere = 3D. Hex = 72k interaction/debug.
                modes stay semantically isolated; coherence is derived, not destructive to stored frames.
              </div>

              <div className="space-y-2">
                <div className="text-sm text-slate-300">Surface</div>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    className={`flex-1 rounded-2xl gap-1 ${surfaceMode === "lattice288" ? "ring-2 ring-amber-400/80" : ""}`}
                    onClick={() => setSurfaceMode("lattice288")}
                  >
                    <Globe className="w-4 h-4" /> 288 lattice
                  </Button>
                  <Button
                    variant="secondary"
                    className={`flex-1 rounded-2xl gap-1 ${surfaceMode === "hex72000" ? "ring-2 ring-amber-400/80" : ""}`}
                    onClick={() => setSurfaceMode("hex72000")}
                  >
                    <Hexagon className="w-4 h-4" /> 72k hex
                  </Button>
                </div>
              </div>

              {surfaceMode === "lattice288" ? (
                <div className="space-y-2">
                  <div className="text-sm text-slate-300">Projection</div>
                  <select
                    value={projection}
                    onChange={(e) => setProjection(/** @type {'flat' | 'diamond' | 'cylinder' | 'spheroid'} */ (e.target.value))}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
                  >
                    <option value="flat">Flat 12×24 (debug grid)</option>
                    <option value="diamond">Diamond (band-centered inspection)</option>
                    <option value="cylinder">Cylinder (wrapped sector, linear band)</option>
                    <option value="spheroid">Sphere (3D truth, Three.js)</option>
                  </select>
                </div>
              ) : null}
              {surfaceMode === "lattice288" && projection === "spheroid" ? (
                <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-800/70">
                  <span className="text-sm text-slate-300">Merge pole rows (12→1 at each cap)</span>
                  <Switch checked={mergePoles} onCheckedChange={setMergePoles} />
                </div>
              ) : null}

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="p-3 rounded-2xl bg-slate-800/70">
                  <div className="text-slate-400">{surfaceMode === "lattice288" ? "Family cells" : "Hexes"}</div>
                  <div className="text-lg font-semibold">
                    {(surfaceMode === "lattice288" ? displayFamilyCells : displayHexes).length.toLocaleString()}
                  </div>
                </div>
                <div className="p-3 rounded-2xl bg-slate-800/70">
                  <div className="text-slate-400">Families</div>
                  <div className="text-lg font-semibold">288</div>
                </div>
                <div className="p-3 rounded-2xl bg-slate-800/70">
                  <div className="text-slate-400">Areas</div>
                  <div className="text-lg font-semibold">12</div>
                </div>
                <div className="p-3 rounded-2xl bg-slate-800/70">
                  <div className="text-slate-400">Frame</div>
                  <div className="text-lg font-semibold">
                    {frameIndex + 1} / {frameCount}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm text-slate-300">Search hex / family / area / dominant index</div>
                <div className="flex gap-2">
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="id, family_id, area_id, dominant_area…"
                    className="bg-slate-800 border-slate-700"
                  />
                  <Button variant="secondary" onClick={focusHexBySearch} className="rounded-2xl">
                    <Search className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm text-slate-300">Render mode (one meaning each)</div>
                <select
                  value={renderMode}
                  onChange={(e) => setRenderMode(/** @type {RenderMode} */ (e.target.value))}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
                >
                  {modeSelectOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                {!debugParam ? (
                  <div className="text-xs text-slate-500">Add ?debug=1 to URL to expose legacy family spectrum (misleading).</div>
                ) : null}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-300">Playback</span>
                  <Button variant="secondary" className="rounded-2xl" onClick={() => setIsPlaying((v) => !v)}>
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </Button>
                </div>
                <div className="text-xs text-slate-400">Speed (ms/frame): {playbackMs}</div>
                <Slider value={[playbackMs]} min={40} max={1200} step={10} onValueChange={(v) => setPlaybackMs(v[0])} />
                <Slider value={[frameIndex]} min={0} max={Math.max(0, frameCount - 1)} step={1} onValueChange={(v) => setFrameIndex(v[0])} />
              </div>

              <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-800/70">
                <div className="flex items-center gap-2 text-sm">
                  <Pin className="w-4 h-4" /> Pin selection across frames
                </div>
                <Switch checked={pinSelection} onCheckedChange={setPinSelection} />
              </div>

              <div className="space-y-2">
                <div className="text-sm text-slate-300">Coherence preprocessing (derived)</div>
                <div className="flex items-center justify-between gap-2">
                  <Switch checked={coherenceOn} onCheckedChange={setCoherenceOn} />
                  <select
                    value={coherenceKind}
                    onChange={(e) => setCoherenceKind(/** @type {any} */ (e.target.value))}
                    className="flex-1 rounded-xl border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-100"
                  >
                    <option value="area_scores">Neighbor avg area_scores → re-argmax</option>
                    <option value="dominance">Smooth dominance scalar</option>
                    <option value="stability">Smooth stability scalar</option>
                  </select>
                </div>
              </div>

              {surfaceMode === "hex72000" ? (
                <div className="space-y-3">
                  <div className="text-sm text-slate-300">Base hex radius: {hexSize}</div>
                  <Slider value={[hexSize]} min={4} max={12} step={1} onValueChange={(v) => setHexSize(v[0])} />
                </div>
              ) : null}

              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm">
                    <Layers className="w-4 h-4" /> Grid stroke
                  </div>
                  <Switch checked={showGridStroke} onCheckedChange={setShowGridStroke} />
                </div>
                <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm">
                    <Eye className="w-4 h-4" /> Labels
                  </div>
                  <Switch checked={showLabels} onCheckedChange={setShowLabels} />
                </div>
              </div>

              {surfaceMode === "hex72000" ? (
                <div className="grid grid-cols-3 gap-2">
                  <Button variant="secondary" className="rounded-2xl" onClick={() => zoomBy(1.25)}>
                    <ZoomIn className="w-4 h-4" />
                  </Button>
                  <Button variant="secondary" className="rounded-2xl" onClick={() => zoomBy(0.8)}>
                    <ZoomOut className="w-4 h-4" />
                  </Button>
                  <Button variant="secondary" className="rounded-2xl" onClick={resetView}>
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="bg-slate-900/80 border-slate-800 rounded-2xl shadow-2xl">
            <CardHeader>
              <CardTitle className="text-lg">Inspection</CardTitle>
            </CardHeader>
            <CardContent>
              {infoHex ? (
                <div className="space-y-3 text-sm max-h-[50vh] overflow-y-auto pr-1">
                  <div>
                    <div className="text-slate-400">Hex ID</div>
                    <div className="font-medium break-all">{infoHex.id}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary" className="rounded-xl">
                      family {String(infoHex.family_id)}
                    </Badge>
                    <Badge variant="secondary" className="rounded-xl">
                      area_id {String(infoHex.area_id)}
                    </Badge>
                    <Badge variant="secondary" className="rounded-xl">
                      dominant {infoHex.dominant_area}
                    </Badge>
                    <Badge variant="secondary" className="rounded-xl">
                      q {infoHex.q}
                    </Badge>
                    <Badge variant="secondary" className="rounded-xl">
                      r {infoHex.r}
                    </Badge>
                    {infoHex.sector != null ? (
                      <Badge variant="secondary" className="rounded-xl">
                        sector {infoHex.sector}
                      </Badge>
                    ) : null}
                    {infoHex.band != null ? (
                      <Badge variant="secondary" className="rounded-xl">
                        band {infoHex.band}
                      </Badge>
                    ) : null}
                  </div>
                  <div>
                    <div className="text-slate-400 mb-1">area_scores[12]</div>
                    <pre className="text-[10px] leading-tight bg-slate-950/80 p-2 rounded-xl overflow-x-auto">
                      [{infoHex.area_scores.map((x) => x.toFixed(3)).join(", ")}]
                    </pre>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-3 rounded-2xl bg-slate-800/70">
                      <div className="text-slate-400">Dominance</div>
                      <div className="font-semibold">{infoHex.dominance.toFixed(4)}</div>
                    </div>
                    <div className="p-3 rounded-2xl bg-slate-800/70">
                      <div className="text-slate-400">Stability</div>
                      <div className="font-semibold">{infoHex.stability.toFixed(4)}</div>
                    </div>
                    {infoHex.contradiction != null ? (
                      <div className="p-3 rounded-2xl bg-slate-800/70">
                        <div className="text-slate-400">Contradiction</div>
                        <div className="font-semibold">{infoHex.contradiction.toFixed(4)}</div>
                      </div>
                    ) : null}
                    {infoHex.activation != null ? (
                      <div className="p-3 rounded-2xl bg-slate-800/70">
                        <div className="text-slate-400">Activation</div>
                        <div className="font-semibold">{infoHex.activation.toFixed(4)}</div>
                      </div>
                    ) : null}
                  </div>
                  {coherenceOn && rawSelectedHex ? (
                    <div className="rounded-xl border border-slate-700 p-2 text-xs text-slate-300">
                      <div className="font-semibold text-slate-200 mb-1">Raw (same frame, no coherence)</div>
                      <div>dominance {rawSelectedHex.dominance.toFixed(4)} → display {selectedHex?.dominance.toFixed(4)}</div>
                      <div>
                        dominant {rawSelectedHex.dominant_area} → display {selectedHex?.dominant_area}
                      </div>
                    </div>
                  ) : null}
                  {frameIndex > 0 && prevFrameHexForSelected ? (
                    <div className="rounded-xl border border-slate-700 p-2 text-xs text-slate-300 space-y-1">
                      <div className="font-semibold text-slate-200">vs previous frame</div>
                      <div>prev dominant {prevFrameHexForSelected.dominant_area}</div>
                      <div>delta_dominance {(infoHex.delta_dominance ?? 0).toFixed(5)}</div>
                      {infoHex.delta_activation != null ? <div>delta_activation {infoHex.delta_activation.toFixed(5)}</div> : null}
                      <div>area_switched {String(!!infoHex.area_switched)}</div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="text-sm text-slate-400">Hover or click a hex to inspect it.</div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-slate-900/80 border-slate-800 rounded-2xl shadow-2xl">
            <CardHeader>
              <CardTitle className="text-lg">Dominance mass by area (display)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {byArea.map(([areaIdx, value]) => (
                  <div key={areaIdx} className="space-y-1">
                    <div className="flex justify-between text-xs text-slate-300">
                      <span>area {areaIdx}</span>
                      <span>{value.toFixed(1)}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${(value / Math.max(byArea[0][1], 1e-9)) * 100}%`,
                          background: `rgb(${[
                            [220, 38, 38],
                            [234, 88, 12],
                            [202, 138, 4],
                            [22, 163, 74],
                            [5, 150, 105],
                            [6, 182, 212],
                            [37, 99, 235],
                            [79, 70, 229],
                            [124, 58, 237],
                            [168, 85, 247],
                            [217, 70, 239],
                            [236, 72, 153],
                          ][areaIdx]
                            .map((c) => Math.round(c * 0.85))
                            .join(",")})`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        <RelationsPanel relations={datasetRelations} appearDisappear={datasetAppearDisappear} />
        </div>

        <Card className="bg-slate-900/80 border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
          <CardContent className="p-0">
            <div className="relative h-[78vh] min-h-[680px]" ref={wrapRef}>
              {surfaceMode === "lattice288" && projection === "flat" ? (
                <FamilyLatticeFlatCanvas
                  cells={displayFamilyCells}
                  renderMode={renderMode}
                  selectedId={selectedId}
                  hoveredId={hoveredId}
                  search={search}
                  onSelect={setSelectedId}
                  onHover={setHoveredId}
                />
              ) : null}
              {surfaceMode === "lattice288" && projection === "diamond" ? (
                <FamilyLatticeDiamondCanvas
                  cells={displayFamilyCells}
                  renderMode={renderMode}
                  selectedId={selectedId}
                  hoveredId={hoveredId}
                  search={search}
                  onSelect={setSelectedId}
                  onHover={setHoveredId}
                />
              ) : null}
              {surfaceMode === "lattice288" && (projection === "cylinder" || projection === "spheroid") ? (
                <FamilyLatticeThreeView
                  projection={projection === "cylinder" ? "cylinder" : "spheroid"}
                  mergePoles={mergePoles}
                  cells={displayFamilyCells}
                  renderMode={renderMode}
                  selectedId={selectedId}
                  hoveredId={hoveredId}
                  onSelect={setSelectedId}
                  onHover={setHoveredId}
                />
              ) : null}
              {surfaceMode === "hex72000" ? (
                <canvas
                  ref={canvasRef}
                  className="absolute inset-0 cursor-grab active:cursor-grabbing"
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={() => {
                    draggingRef.current = false;
                    setHoveredId(null);
                  }}
                  onWheel={handleWheel}
                />
              ) : null}

              <div className="absolute top-4 left-4 flex flex-wrap gap-2 max-w-[75%] pointer-events-none">
                {surfaceMode === "hex72000" ? (
                  <Badge className="rounded-xl bg-slate-950/80 text-slate-100 border border-slate-700 pointer-events-none">zoom {zoom.toFixed(2)}x</Badge>
                ) : (
                  <Badge className="rounded-xl bg-slate-950/80 text-slate-100 border border-slate-700 pointer-events-none">
                    projection {projection}
                  </Badge>
                )}
                <Badge className="rounded-xl bg-slate-950/80 text-slate-100 border border-slate-700 pointer-events-none">mode {renderMode}</Badge>
                <Badge className="rounded-xl bg-slate-950/80 text-slate-100 border border-slate-700 pointer-events-none">
                  frame {frameIndex + 1}/{frameCount}
                </Badge>
                {coherenceOn ? (
                  <Badge className="rounded-xl bg-amber-950/80 text-amber-100 border border-amber-800 pointer-events-none">coherence {coherenceKind}</Badge>
                ) : null}
                {hoveredHex ? (
                  <Badge className="rounded-xl bg-slate-950/80 text-slate-100 border border-slate-700 pointer-events-none">hover {hoveredHex.id}</Badge>
                ) : null}
                {selectedHex ? (
                  <Badge className="rounded-xl bg-slate-950/80 text-slate-100 border border-slate-700 pointer-events-none">selected {selectedHex.id}</Badge>
                ) : null}
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
