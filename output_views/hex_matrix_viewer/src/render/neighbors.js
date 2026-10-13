/** Axial directions (pointy-top / flat-top consistent with hexToPixel in viewer). */
export const AXIAL_DIRS = [
  { q: 1, r: 0 },
  { q: 1, r: -1 },
  { q: 0, r: -1 },
  { q: -1, r: 0 },
  { q: -1, r: 1 },
  { q: 0, r: 1 },
];

/**
 * @param {import('../schema/hexSchema.js').HexState[]} hexes
 * @returns {Map<string, import('../schema/hexSchema.js').HexState>}
 */
export function buildCoordMap(hexes) {
  const m = new Map();
  for (const h of hexes) {
    m.set(`${h.q},${h.r}`, h);
  }
  return m;
}

/**
 * @param {import('../schema/hexSchema.js').HexState} h
 * @param {Map<string, import('../schema/hexSchema.js').HexState>} coordMap
 */
export function getNeighbors(h, coordMap) {
  /** @type {import('../schema/hexSchema.js').HexState[]} */
  const out = [];
  for (const d of AXIAL_DIRS) {
    const n = coordMap.get(`${h.q + d.q},${h.r + d.r}`);
    if (n) out.push(n);
  }
  return out;
}
