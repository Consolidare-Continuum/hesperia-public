import { N_AREAS, argmax12, clamp01 } from "../schema/hexSchema.js";
import { buildCoordMap, getNeighbors } from "./neighbors.js";

function sumVec(v) {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += v[i];
  return s;
}

/**
 * One deterministic pass: neighbor-averaged area score vectors + re-derived dominant_area/dominance.
 * Non-destructive: returns new hex array.
 * @param {import('../schema/hexSchema.js').HexState[]} hexes
 */
export function coherenceAreaScoresPass(hexes) {
  const coordMap = buildCoordMap(hexes);
  return hexes.map((h) => {
    const neigh = getNeighbors(h, coordMap);
    const acc = new Array(N_AREAS).fill(0);
    for (let i = 0; i < N_AREAS; i++) acc[i] += h.area_scores[i];
    for (const n of neigh) {
      for (let i = 0; i < N_AREAS; i++) acc[i] += n.area_scores[i];
    }
    const w = 1 + neigh.length;
    for (let i = 0; i < N_AREAS; i++) acc[i] /= w;
    const dominant_area = argmax12(acc);
    const dom = clamp01(acc[dominant_area] / (sumVec(acc) + 1e-9));
    return {
      ...h,
      area_scores: acc,
      dominant_area,
      dominance: dom,
    };
  });
}

/**
 * Scalar smoothing for dominance / stability heat views.
 * @param {import('../schema/hexSchema.js').HexState[]} hexes
 * @param {'dominance' | 'stability'} field
 */
export function coherenceScalarPass(hexes, field) {
  const coordMap = buildCoordMap(hexes);
  return hexes.map((h) => {
    const neigh = getNeighbors(h, coordMap);
    let s = /** @type {number} */ (h[field]);
    for (const n of neigh) s += /** @type {number} */ (n[field]);
    const v = clamp01(s / (1 + neigh.length));
    return { ...h, [field]: v };
  });
}
