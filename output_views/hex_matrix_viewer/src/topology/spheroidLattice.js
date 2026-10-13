/**
 * Canonical 12×24 family lattice F(s,b) on a spheroid shell.
 * s = sector (0..11), b = band (0..23). Linear index: row-major with sector across, band down.
 *
 * Adjacency (explicit):
 * - left:  F((s - 1) mod 12, b)
 * - right: F((s + 1) mod 12, b)
 * - up:    F(s, b - 1) when b > 0
 * - down:  F(s, b + 1) when b < 23
 */

export const SECTORS = 12;
export const BANDS = 24;
export const N_FAMILY_CELLS = SECTORS * BANDS; // 288

/**
 * @param {number} s
 * @param {number} b
 */
export function familyLinearIndex(s, b) {
  return b * SECTORS + s;
}

/**
 * @param {number} idx 0..287
 * @returns {{ s: number; b: number }}
 */
export function parseFamilyLinear(idx) {
  const s = idx % SECTORS;
  const b = Math.floor(idx / SECTORS);
  return { s, b };
}

/**
 * Matches existing mock: family_id = sector*24 + band (sector was area_id, band was fam_in_area).
 * @param {number} familyId 0..287
 */
export function familyIdToSB(familyId) {
  const s = Math.floor(familyId / BANDS);
  const b = familyId % BANDS;
  return { s, b };
}

/**
 * Inverse: (s,b) -> family_id 0..287
 * @param {number} s
 * @param {number} b
 */
export function sbToFamilyId(s, b) {
  return s * BANDS + b;
}

/**
 * Neighbors with boundary semantics (no vertical wrap).
 * @param {number} s
 * @param {number} b
 */
export function latticeNeighbors(s, b) {
  const left = { s: (s - 1 + SECTORS) % SECTORS, b };
  const right = { s: (s + 1) % SECTORS, b };
  /** @type {{ s: number; b: number }[]} */
  const out = [left, right];
  if (b > 0) out.push({ s, b: b - 1 });
  if (b < BANDS - 1) out.push({ s, b: b + 1 });
  return out;
}

/**
 * Diamond inspection layout (not spherical geometry): band-centered rows, equator widest.
 * Row b has width W = 1 + min(b, 23 − b). Map sector s → column col = floor(s · W / 12) (12 sectors distributed across W slots; poles narrow).
 * Still exactly 288 cells F(s,b); order and adjacency unchanged — only screen placement differs.
 *
 * @param {number} s
 * @param {number} b
 * @returns {{ width: number; col: number; row: number }}
 */
export function diamondLayout(s, b) {
  const width = 1 + Math.min(b, BANDS - 1 - b);
  const col = Math.min(width - 1, Math.floor((s * width) / 12));
  return { width, col, row: b };
}

/**
 * Projection modes: only (x,y,z) change; (s,b) indexing and adjacency do not.
 * @typedef {'flat' | 'cylinder' | 'spheroid'} ProjectionMode
 */

/**
 * Single mapping for all 3D/2D projections (Codex spec).
 * - flat: integer grid (x=s, y=b, z=0) — useful for 2D layout math; canvas may still use pixel mapping.
 * - cylinder: horizontal wrap, vertical stays band index (linear).
 * - spheroid: full sphere with phi from v = b/(B-1); optional pole collapse merges 12 cells at each cap.
 *
 * @param {number} s sector 0..S-1
 * @param {number} b band 0..B-1
 * @param {ProjectionMode} mode
 * @param {{ R?: number; poleCollapse?: boolean }} [opts] R default 10 (match task); poleCollapse default false for strict grid, set true for cleaner poles
 * @returns {{ x: number; y: number; z: number }}
 */
export function project(s, b, mode, opts = {}) {
  const S = SECTORS;
  const B = BANDS;
  const R = opts.R ?? 10;
  const u = s / S;
  const v = b / (B - 1);
  const theta = 2 * Math.PI * u;
  const phi = Math.PI * (v - 0.5);

  if (mode === "flat") {
    return { x: s, y: b, z: 0 };
  }

  if (mode === "cylinder") {
    return {
      x: R * Math.cos(theta),
      y: b,
      z: R * Math.sin(theta),
    };
  }

  if (mode === "spheroid") {
    if (opts.poleCollapse) {
      if (b === 0) return { x: 0, y: R, z: 0 };
      if (b === B - 1) return { x: 0, y: -R, z: 0 };
    }
    const cosPhi = Math.cos(phi);
    const sinPhi = Math.sin(phi);
    return {
      x: R * cosPhi * Math.cos(theta),
      y: R * sinPhi,
      z: R * cosPhi * Math.sin(theta),
    };
  }

  return { x: 0, y: 0, z: 0 };
}

/**
 * @deprecated use {@link project}(s, b, 'spheroid', { R: radius, poleCollapse })
 */
export function spherePosition(s, b, radius = 1) {
  return project(s, b, "spheroid", { R: radius, poleCollapse: false });
}

/**
 * Legacy cylinder: normalized band height. Prefer {@link project}(..., "cylinder") for Codex layout (y = b).
 */
export function cylinderPosition(s, b, cylRadius = 1, height = 2.2) {
  const theta = (2 * Math.PI * s) / SECTORS;
  return {
    x: cylRadius * Math.cos(theta),
    y: (b / (BANDS - 1) - 0.5) * height,
    z: cylRadius * Math.sin(theta),
  };
}

/**
 * Flat Mercator-like: X = sector, Y = band (north at top, b=0).
 * Returns normalized 0..1 cell center.
 * @param {number} s
 * @param {number} b
 */
export function flatNormalizedCenter(s, b) {
  return {
    x: (s + 0.5) / SECTORS,
    y: (b + 0.5) / BANDS,
  };
}
