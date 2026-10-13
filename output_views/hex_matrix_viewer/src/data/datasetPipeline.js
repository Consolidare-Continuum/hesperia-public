import { buildSemanticLayout } from "../layout/familyLayout.js";
import { N_HEX, normalizeHex } from "../schema/hexSchema.js";

/**
 * Load JSON `{ frames: [...] }`, apply semantic layout when q/r missing (72k rows),
 * normalize to strict HexState.
 * @param {any} json
 */
export function loadDataset(json) {
  if (!json || !Array.isArray(json.frames)) throw new Error("JSON must have { frames: [...] }");
  const layout = buildSemanticLayout();
  const frames = json.frames.map((fr, fi) => {
    const t = typeof fr.t === "number" ? fr.t : fi;
    const rawHexes = fr.hexes || [];
    const hexes = rawHexes.map((h, i) => {
      let raw = h;
      if ((h.q == null || h.r == null) && rawHexes.length === N_HEX && i < layout.length) {
        const L = layout[i];
        raw = {
          ...h,
          q: L.q,
          r: L.r,
          family_id: h.family_id ?? L.family_id,
          area_id: h.area_id ?? L.area_id,
        };
      }
      return normalizeHex(raw, raw.q ?? 0, raw.r ?? 0);
    });
    return { t, hexes };
  });
  return { frames };
}
