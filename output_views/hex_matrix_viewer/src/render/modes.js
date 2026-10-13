/**
 * One render mode = one meaning. Fill color only (boundary draws edges separately).
 */

import { N_AREAS } from "../schema/hexSchema.js";

/** 12 categorical area colors (RGB) — no mixing in dominant-area mode. */
export const AREA_RGB = [
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
];

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

/**
 * Dominant area: exactly one category RGB; brightness from dominance only.
 * @param {import('../schema/hexSchema.js').HexState} h
 */
export function colorDominantArea(h) {
  const rgb = AREA_RGB[((h.dominant_area % N_AREAS) + N_AREAS) % N_AREAS];
  const inten = 0.22 + 0.78 * clamp(h.dominance, 0, 1);
  return `rgb(${Math.round(rgb[0] * inten)}, ${Math.round(rgb[1] * inten)}, ${Math.round(rgb[2] * inten)})`;
}

/** Single-hue heat: dominance only. */
export function colorDominanceHeat(h) {
  const v = clamp(h.dominance, 0, 1);
  const hue = lerp(230, 12, v);
  const light = lerp(22, 58, v);
  return `hsl(${hue} 78% ${light}%)`;
}

/** Single-hue heat: stability only. */
export function colorStabilityHeat(h) {
  const v = clamp(h.stability, 0, 1);
  const hue = lerp(8, 145, v);
  return `hsl(${hue} 72% ${lerp(28, 52, v)}%)`;
}

/**
 * Delta vs previous frame (precomputed on h: delta_dominance, area_switched).
 */
export function colorDeltaMap(h) {
  const d = typeof h.delta_dominance === "number" ? h.delta_dominance : 0;
  const t = clamp(Math.abs(d) * 4, 0, 1);
  if (Math.abs(d) < 0.004) return `rgba(120, 128, 140, ${0.35 + 0.35 * (1 - t)})`;
  if (d > 0) return `rgba(34, 197, 94, ${0.35 + 0.55 * t})`;
  return `rgba(239, 68, 68, ${0.35 + 0.55 * t})`;
}

/** Muted base for boundary mode interior. */
export function colorBoundaryFill(h) {
  const rgb = AREA_RGB[((h.dominant_area % N_AREAS) + N_AREAS) % N_AREAS];
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 0.22)`;
}

/**
 * Family layout inspect: stable pseudo-color from family_id (not spiral index).
 * @param {import('../schema/hexSchema.js').HexState} h
 */
export function colorFamilyLayoutInspect(h) {
  let hsh = 2166136261;
  const s = String(h.family_id);
  for (let i = 0; i < s.length; i++) {
    hsh ^= s.charCodeAt(i);
    hsh = Math.imul(hsh, 16777619);
  }
  const hue = (hsh >>> 0) % 360;
  return `hsl(${hue} 42% 46%)`;
}

/**
 * Debug-only: legacy rainbow by numeric index (misleading) — keyed by family_id hash, not array index.
 * @deprecated semantic trap if used as primary
 */
export function colorFamilySpectrumDebug(h, spiralIndex) {
  const hue = (spiralIndex * 17) % 360;
  const sat = 55;
  const light = 28 + Math.round((h.dominance || 0.5) * 28);
  return `hsl(${hue} ${sat}% ${light}%)`;
}

/**
 * @typedef {'dominant_area' | 'dominance_heat' | 'stability_heat' | 'delta' | 'boundary' | 'family_layout' | 'family_spectrum_debug'} RenderMode
 */

/**
 * @param {import('../schema/hexSchema.js').HexState} h
 * @param {RenderMode} mode
 * @param {number} [spiralIndex] only for debug spectrum
 */
export function getFillColor(h, mode, spiralIndex = 0) {
  switch (mode) {
    case "dominant_area":
      return colorDominantArea(h);
    case "dominance_heat":
      return colorDominanceHeat(h);
    case "stability_heat":
      return colorStabilityHeat(h);
    case "delta":
      return colorDeltaMap(h);
    case "boundary":
      return colorBoundaryFill(h);
    case "family_layout":
      return colorFamilyLayoutInspect(h);
    case "family_spectrum_debug":
      return colorFamilySpectrumDebug(h, spiralIndex);
    default:
      return colorDominantArea(h);
  }
}
