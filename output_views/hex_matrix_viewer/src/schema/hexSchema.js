/**
 * Strict HESPERIA hex / frame data contract (viewer-side).
 * @see README.md — adapter normalizes legacy JSON into this shape.
 */

export const N_AREAS = 12;
export const N_FAMILIES = 288;
export const HEX_PER_FAMILY = 250;
export const N_HEX = 72000;

/** @typedef {{ r: number; g: number; b: number }} RGB */

/**
 * @typedef {Object} HexState
 * @property {string} id
 * @property {string|number} family_id
 * @property {string|number} area_id
 * @property {number} q
 * @property {number} r
 * @property {number[]} area_scores length N_AREAS
 * @property {number} dominant_area 0..N_AREAS-1
 * @property {number} dominance 0..1
 * @property {number} stability 0..1
 * @property {number} [contradiction] 0..1
 * @property {number} [activation] 0..1
 * @property {number} [prev_dominant_area]
 * @property {number} [delta_dominance]
 * @property {number} [delta_activation]
 * @property {boolean} [area_switched]
 */

/**
 * @typedef {Object} Frame
 * @property {number} t
 * @property {HexState[]} hexes
 */

/**
 * @typedef {Object} AreaDriftEntry
 * @property {number} area  0..N_AREAS-1
 * @property {number} drift  signed L1 mean delta vs session imprint
 * @property {string} [theme_marker]
 */

/**
 * TMX-08: Session-level relation block (Y+Z drift).
 * @typedef {Object} RelationsBlock
 * @property {AreaDriftEntry[]} area_drift
 * @property {number} [global_drift]
 * @property {string} [parity_note]
 */

/**
 * @typedef {Object} SignalEntry
 * @property {string} label
 * @property {number} [onset_frame]
 * @property {number} [offset_frame]
 * @property {number} [dominance_peak]
 */

/**
 * TMX-09: Appear/disappear signals across iterations.
 * @typedef {Object} AppearDisappearBlock
 * @property {SignalEntry[]} [appeared]
 * @property {SignalEntry[]} [disappeared]
 * @property {string} [dominant_shift]
 */

/**
 * @typedef {Object} Dataset
 * @property {Frame[]} frames
 * @property {RelationsBlock} [relations]
 * @property {AppearDisappearBlock} [appear_disappear]
 */

export function clamp01(x) {
  return Math.max(0, Math.min(1, x));
}

/**
 * Argmax of array; ties broken by lowest index.
 * @param {number[]} scores
 */
export function argmax12(scores) {
  let best = 0;
  for (let i = 1; i < scores.length; i++) {
    if (scores[i] > scores[best]) best = i;
  }
  return best;
}

/**
 * Normalize one hex from export or legacy mock.
 * @param {any} raw
 * @param {number} q
 * @param {number} r
 * @returns {HexState}
 */
export function normalizeHex(raw, q, r) {
  const id = raw?.id != null ? String(raw.id) : `H-${q},${r}`;
  const family_id = raw?.family_id != null ? raw.family_id : raw?.family != null ? String(raw.family) : "F000";
  const area_id = raw?.area_id != null ? raw.area_id : raw?.area != null ? String(raw.area) : "A01";

  let area_scores = Array.isArray(raw?.area_scores) ? raw.area_scores.slice(0, N_AREAS) : null;
  if (!area_scores || area_scores.length !== N_AREAS) {
    area_scores = new Array(N_AREAS).fill(0);
    const legacyArea = typeof raw?.areaIndex === "number" ? raw.areaIndex : parseInt(String(area_id).replace(/\D/g, ""), 10);
    const idx = Number.isFinite(legacyArea) ? (legacyArea - 1 + N_AREAS * 10) % N_AREAS : 0;
    const v = typeof raw?.value === "number" ? raw.value : 0.5;
    area_scores[idx] = v;
    for (let i = 0; i < N_AREAS; i++) area_scores[i] += (i === idx ? 0.5 : 0.02) * (0.3 + 0.07 * i);
  }
  for (let i = 0; i < N_AREAS; i++) area_scores[i] = clamp01(Number(area_scores[i]) || 0);

  let dominant_area =
    typeof raw?.dominant_area === "number" ? Math.floor(raw.dominant_area) : argmax12(area_scores);
  dominant_area = ((dominant_area % N_AREAS) + N_AREAS) % N_AREAS;

  const dominance = clamp01(
    typeof raw?.dominance === "number" ? raw.dominance : area_scores[dominant_area] / (sumScores(area_scores) || 1)
  );
  const stability = clamp01(typeof raw?.stability === "number" ? raw.stability : 0.5);

  /** @type {HexState} */
  const out = {
    id,
    family_id,
    area_id,
    q,
    r,
    area_scores,
    dominant_area,
    dominance,
    stability,
  };
  if (typeof raw?.contradiction === "number") out.contradiction = clamp01(raw.contradiction);
  if (typeof raw?.activation === "number") out.activation = clamp01(raw.activation);
  if (typeof raw?.prev_dominant_area === "number") out.prev_dominant_area = raw.prev_dominant_area;
  if (typeof raw?.delta_dominance === "number") out.delta_dominance = raw.delta_dominance;
  if (typeof raw?.delta_activation === "number") out.delta_activation = raw.delta_activation;
  if (typeof raw?.area_switched === "boolean") out.area_switched = raw.area_switched;
  return out;
}

function sumScores(s) {
  let t = 0;
  for (let i = 0; i < s.length; i++) t += s[i];
  return t;
}

