/**
 * Deterministic semantic layout: 12 macro areas × 24 families/area × 250 hexes/family.
 * Global index order does not define screen position — placement is derived from
 * (area_id, family_slot) anchors + local spiral inside each family cluster.
 *
 * Spacing constants chosen so local spirals (~radius ~15–18 hex) do not overlap
 * between adjacent family anchors within an area, and area blocks are separated.
 */

import { N_AREAS, N_FAMILIES, HEX_PER_FAMILY, N_HEX } from "../schema/hexSchema.js";

/** @typedef {{ q: number; r: number }} Axial */

const DIRS = [
  { q: 1, r: 0 },
  { q: 1, r: -1 },
  { q: 0, r: -1 },
  { q: -1, r: 0 },
  { q: -1, r: 1 },
  { q: 0, r: 1 },
];

/**
 * Local hex spiral (same algorithm as legacy viewer) — used only inside a family subzone.
 * @param {number} count
 * @returns {Axial[]}
 */
export function buildHexSpiral(count) {
  const coords = [];
  let q = 0;
  let r = 0;
  coords.push({ q, r });
  if (count === 1) return coords;

  let radius = 1;
  while (coords.length < count) {
    q = -radius;
    r = radius;
    for (let side = 0; side < 6; side++) {
      for (let step = 0; step < radius; step++) {
        if (coords.length >= count) break;
        coords.push({ q, r });
        q += DIRS[side].q;
        r += DIRS[side].r;
      }
    }
    radius++;
  }
  return coords;
}

const LOCAL_SPIRAL = buildHexSpiral(HEX_PER_FAMILY);

/**
 * Area macro-origin on a 3×4 grid of blocks (12 areas).
 * @param {number} areaId 0..11
 * @returns {Axial}
 */
function areaOrigin(areaId) {
  const col = areaId % 3;
  const row = Math.floor(areaId / 3);
  const pitchQ = 520;
  const pitchR = 520;
  return { q: col * pitchQ, r: row * pitchR };
}

/**
 * One of 24 family anchors inside an area (4×6 lattice).
 * @param {number} areaId
 * @param {number} famInArea 0..23
 */
function familyAnchor(areaId, famInArea) {
  const base = areaOrigin(areaId);
  const cols = 6;
  const fc = famInArea % cols;
  const fr = Math.floor(famInArea / cols);
  const step = 56;
  return { q: base.q + fc * step + 12, r: base.r + fr * step + 12 };
}

/**
 * @typedef {{ q: number; r: number; family_id: number; area_id: number }} LayoutCell
 */

/**
 * Build full 72k layout: deterministic, stable family/area regions, no global spiral fill.
 * @returns {LayoutCell[]}
 */
export function buildSemanticLayout() {
  if (N_AREAS * 24 !== N_FAMILIES) throw new Error("Layout assumes 24 families per area");
  if (N_FAMILIES * HEX_PER_FAMILY !== N_HEX) throw new Error("Layout count mismatch");

  /** @type {LayoutCell[]} */
  const out = [];
  for (let areaId = 0; areaId < N_AREAS; areaId++) {
    for (let famInArea = 0; famInArea < 24; famInArea++) {
      const family_id = areaId * 24 + famInArea;
      const anchor = familyAnchor(areaId, famInArea);
      for (let i = 0; i < HEX_PER_FAMILY; i++) {
        const loc = LOCAL_SPIRAL[i];
        out.push({
          q: anchor.q + loc.q,
          r: anchor.r + loc.r,
          family_id,
          area_id: areaId,
        });
      }
    }
  }
  return out;
}
