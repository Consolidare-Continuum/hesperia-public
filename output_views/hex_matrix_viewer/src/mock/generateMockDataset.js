import { buildSemanticLayout } from "../layout/familyLayout.js";
import { N_AREAS, N_HEX, clamp01, argmax12 } from "../schema/hexSchema.js";

const FRAMES = 24;

function hashString(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function sumScores(s) {
  let t = 0;
  for (let i = 0; i < s.length; i++) t += s[i];
  return t;
}

/**
 * Attach prev_dominant_area, delta_dominance, delta_activation, area_switched per hex id.
 * @param {{ t: number; hexes: any[] }[]} frames
 */
export function attachFrameTransitions(frames) {
  for (let fi = 0; fi < frames.length; fi++) {
    const prev = fi > 0 ? frames[fi - 1].hexes : null;
    const prevById = prev ? new Map(prev.map((x) => [x.id, x])) : null;
    for (const h of frames[fi].hexes) {
      if (!prevById) continue;
      const p = prevById.get(h.id);
      if (!p) continue;
      h.prev_dominant_area = p.dominant_area;
      h.delta_dominance = (h.dominance ?? 0) - (p.dominance ?? 0);
      if (typeof h.activation === "number" || typeof p.activation === "number") {
        h.delta_activation = (h.activation ?? 0) - (p.activation ?? 0);
      }
      h.area_switched = p.dominant_area !== h.dominant_area;
    }
  }
}

/**
 * @returns {import('../schema/hexSchema.js').Dataset}
 */
export function generateMockDataset() {
  const layout = buildSemanticLayout();
  /** @type {{ t: number; hexes: import('../schema/hexSchema.js').HexState[] }[]} */
  const frames = [];

  for (let frameIndex = 0; frameIndex < FRAMES; frameIndex++) {
    const t = frameIndex / Math.max(1, FRAMES - 1);
    const hexes = layout.map((cell, i) => {
      const seed = hashString(`v2:${cell.family_id}:${i}`);
      const area_scores = new Array(N_AREAS).fill(0);
      for (let a = 0; a < N_AREAS; a++) {
        const base = a === cell.area_id ? 0.38 : 0.04;
        const wave = 0.5 + 0.5 * Math.sin(t * Math.PI * 2 + i * 0.00035 + a * 0.31);
        const jitter = ((seed >> (a * 3)) & 1023) / 2500;
        area_scores[a] = clamp01(base + wave * 0.14 + jitter);
      }
      area_scores[cell.area_id] = clamp01(area_scores[cell.area_id] + 0.28 + 0.08 * Math.sin(t * Math.PI * 3 + cell.family_id * 0.02));

      const dominant_area = argmax12(area_scores);
      const sum = sumScores(area_scores);
      const dominance = clamp01(area_scores[dominant_area] / (sum + 1e-9));
      const stability = clamp01(
        0.35 + 0.45 * (1 - Math.abs(Math.sin(t * 8 + i * 0.001))) + 0.2 * ((seed >> 11) % 1000) / 1000
      );
      const contradiction = clamp01(0.15 + 0.85 * Math.abs(area_scores[dominant_area] - Math.max(...area_scores.filter((_, j) => j !== dominant_area))));
      const activation = clamp01(0.3 + 0.6 * ((seed >> 5) % 1000) / 1000 + 0.1 * Math.sin(t * Math.PI * 4 + cell.q * 0.001));

      const id = `A${String(cell.area_id + 1).padStart(2, "0")}-F${String(cell.family_id + 1).padStart(3, "0")}-H${String(i + 1).padStart(5, "0")}`;

      return {
        id,
        family_id: cell.family_id,
        area_id: cell.area_id,
        q: cell.q,
        r: cell.r,
        area_scores,
        dominant_area,
        dominance,
        stability,
        contradiction,
        activation,
      };
    });
    frames.push({ t, hexes });
  }

  attachFrameTransitions(frames);

  /** @type {import('../schema/hexSchema.js').RelationsBlock} */
  const relations = {
    area_drift: Array.from({ length: 12 }, (_, i) => ({
      area: i,
      drift: (((i * 7 + 3) % 17) / 17 - 0.5) * 0.4,
      theme_marker: i < 4 ? ["conflict", "anchor", "tension", "release"][i] : undefined,
    })),
    global_drift: 0.12,
    parity_note: "mock: therapist parity within ±0.05 on areas 0-3",
  };

  /** @type {import('../schema/hexSchema.js').AppearDisappearBlock} */
  const appear_disappear = {
    appeared: [
      { label: "A02-family-onset", onset_frame: 3, dominance_peak: 0.72 },
      { label: "A07-theme-marker", onset_frame: 8, dominance_peak: 0.61 },
    ],
    disappeared: [
      { label: "A11-family-offset", offset_frame: 15, dominance_peak: 0.44 },
    ],
    dominant_shift: "A02→A07 progressive onset mid-session",
  };

  return { frames, relations, appear_disappear };
}

export { FRAMES };
