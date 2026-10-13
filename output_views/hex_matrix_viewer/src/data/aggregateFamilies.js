import { N_FAMILY_CELLS, familyIdToSB } from "../topology/spheroidLattice.js";
import { N_AREAS, argmax12, clamp01, normalizeHex } from "../schema/hexSchema.js";

/**
 * Parse numeric family id 0..287 from hex.family_id
 * @param {import('../schema/hexSchema.js').HexState} h
 */
export function numericFamilyIdFromHex(h) {
  if (typeof h.family_id === "number" && Number.isFinite(h.family_id)) {
    return ((h.family_id % N_FAMILY_CELLS) + N_FAMILY_CELLS) % N_FAMILY_CELLS;
  }
  const m = String(h.family_id).match(/(\d+)/);
  if (m) return (parseInt(m[1], 10) - 1 + N_FAMILY_CELLS) % N_FAMILY_CELLS;
  const aid = Number(h.area_id);
  return Number.isFinite(aid) ? Math.min(N_FAMILY_CELLS - 1, Math.max(0, aid)) : 0;
}

/**
 * Aggregate sub-hex rows into one FamilyCell per F(s,b). Deterministic; does not invent adjacency.
 * @param {import('../schema/hexSchema.js').HexState[]} hexes
 * @returns {import('../schema/hexSchema.js').HexState[]}
 */
export function aggregateHexesToFamilyCells(hexes) {
  /** @type {Map<number, import('../schema/hexSchema.js').HexState[]>} */
  const groups = new Map();
  for (const h of hexes) {
    const fid = numericFamilyIdFromHex(h);
    if (!groups.has(fid)) groups.set(fid, []);
    groups.get(fid).push(h);
  }

  /** @type {import('../schema/hexSchema.js').HexState[]} */
  const out = [];
  for (let fid = 0; fid < N_FAMILY_CELLS; fid++) {
    const list = groups.get(fid) || [];
    const { s, b } = familyIdToSB(fid);
    if (list.length === 0) {
      const placeholder = normalizeHex(
        {
          id: `S${s}B${b}`,
          family_id: fid,
          area_id: s,
          area_scores: new Array(N_AREAS).fill(0),
          dominance: 0,
          stability: 0,
        },
        0,
        0
      );
      Object.assign(placeholder, { sector: s, band: b });
      out.push(placeholder);
      continue;
    }

    const accScores = new Array(N_AREAS).fill(0);
    let domSum = 0;
    let stabSum = 0;
    let contraSum = 0;
    let actSum = 0;
    let nContra = 0;
    let nAct = 0;
    for (const h of list) {
      for (let a = 0; a < N_AREAS; a++) accScores[a] += h.area_scores[a];
      domSum += h.dominance;
      stabSum += h.stability;
      if (h.contradiction != null) {
        contraSum += h.contradiction;
        nContra++;
      }
      if (h.activation != null) {
        actSum += h.activation;
        nAct++;
      }
    }
    const n = list.length;
    for (let a = 0; a < N_AREAS; a++) accScores[a] /= n;
    const dominant_area = argmax12(accScores);
    const dominance = clamp01(accScores[dominant_area] / (accScores.reduce((x, y) => x + y, 0) + 1e-9));
    const stability = clamp01(stabSum / n);

    /** @type {import('../schema/hexSchema.js').HexState} */
    const cell = normalizeHex(
      {
        id: `F${String(fid + 1).padStart(3, "0")}-S${s}-B${b}`,
        family_id: fid,
        area_id: s,
        q: s,
        r: b,
        area_scores: accScores,
        dominant_area,
        dominance,
        stability,
        contradiction: nContra ? contraSum / nContra : undefined,
        activation: nAct ? actSum / nAct : undefined,
      },
      s,
      b
    );
    Object.assign(cell, { sector: s, band: b });
    out.push(cell);
  }
  return out;
}

/**
 * @param {import('../schema/hexSchema.js').HexState[][]} framesCells
 */
export function attachFamilyLatticeTransitions(framesCells) {
  for (let fi = 0; fi < framesCells.length; fi++) {
    const prev = fi > 0 ? framesCells[fi - 1] : null;
    if (!prev) continue;
    const pmap = new Map(prev.map((x) => [x.family_id, x]));
    for (const h of framesCells[fi]) {
      const p = pmap.get(h.family_id);
      if (!p) continue;
      h.prev_dominant_area = p.dominant_area;
      h.delta_dominance = (h.dominance ?? 0) - (p.dominance ?? 0);
      h.area_switched = p.dominant_area !== h.dominant_area;
      if (typeof h.activation === "number" || typeof p.activation === "number") {
        h.delta_activation = (h.activation ?? 0) - (p.activation ?? 0);
      }
    }
  }
}
