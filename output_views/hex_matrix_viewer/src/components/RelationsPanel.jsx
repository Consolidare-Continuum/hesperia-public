/**
 * RelationsPanel — displays TMX-08/09 relations + appear/disappear signals
 * when present in the loaded dataset (dataset.relations, dataset.appear_disappear).
 */
import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

/** @param {{ value: number }} p */
function DriftBar({ value }) {
  const pct = Math.round(Math.abs(value) * 100);
  const color = value > 0.15 ? "bg-rose-500" : value > 0.05 ? "bg-amber-400" : "bg-emerald-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct * 3, 100)}%` }} />
      </div>
      <span className="text-[10px] text-slate-400 w-12 text-right">{value >= 0 ? "+" : ""}{value.toFixed(3)}</span>
    </div>
  );
}

/**
 * @param {{
 *   relations: import('../schema/hexSchema.js').RelationsBlock | null,
 *   appearDisappear: import('../schema/hexSchema.js').AppearDisappearBlock | null,
 * }} props
 */
export function RelationsPanel({ relations, appearDisappear }) {
  const [tab, setTab] = useState("relations");
  const hasRelations = relations && Array.isArray(relations.area_drift) && relations.area_drift.length > 0;
  const hasAD = appearDisappear && (appearDisappear.appeared?.length || appearDisappear.disappeared?.length);

  if (!hasRelations && !hasAD) return null;

  return (
    <Card className="bg-slate-900/80 border-slate-800 rounded-2xl shadow-2xl">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          Relations + Signals
          {hasRelations && hasAD ? (
            <div className="flex gap-1 ml-auto">
              <button
                onClick={() => setTab("relations")}
                className={`text-xs px-2 py-0.5 rounded-lg transition-colors ${tab === "relations" ? "bg-slate-700 text-slate-100" : "text-slate-400 hover:text-slate-200"}`}
              >
                Drift
              </button>
              <button
                onClick={() => setTab("ad")}
                className={`text-xs px-2 py-0.5 rounded-lg transition-colors ${tab === "ad" ? "bg-slate-700 text-slate-100" : "text-slate-400 hover:text-slate-200"}`}
              >
                Appear/Disappear
              </button>
            </div>
          ) : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {/* Relations / drift tab */}
        {(tab === "relations" || !hasAD) && hasRelations ? (
          <div className="space-y-2">
            <div className="text-xs text-slate-400">Area drift vs session imprint (L1 mean)</div>
            {relations.area_drift.map((entry) => (
              <div key={entry.area} className="space-y-0.5">
                <div className="flex justify-between text-xs text-slate-300">
                  <span>area {entry.area}</span>
                  {entry.theme_marker ? (
                    <Badge className="rounded bg-slate-800 text-slate-300 text-[10px] px-1 py-0">{entry.theme_marker}</Badge>
                  ) : null}
                </div>
                <DriftBar value={entry.drift} />
              </div>
            ))}
            {relations.parity_note ? (
              <div className="text-[10px] text-slate-400 border-t border-slate-800 pt-2">{relations.parity_note}</div>
            ) : null}
          </div>
        ) : null}

        {/* Appear/disappear tab */}
        {(tab === "ad" || !hasRelations) && hasAD ? (
          <div className="space-y-3">
            {appearDisappear.appeared?.length ? (
              <div>
                <div className="text-xs text-emerald-400 mb-1">Appeared ({appearDisappear.appeared.length})</div>
                <div className="space-y-1">
                  {appearDisappear.appeared.map((sig, i) => (
                    <div key={i} className="flex items-center justify-between text-xs text-slate-300 bg-emerald-950/30 rounded px-2 py-1">
                      <span>{sig.label}</span>
                      <span className="text-slate-400">{sig.onset_frame != null ? `f${sig.onset_frame}` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {appearDisappear.disappeared?.length ? (
              <div>
                <div className="text-xs text-rose-400 mb-1">Disappeared ({appearDisappear.disappeared.length})</div>
                <div className="space-y-1">
                  {appearDisappear.disappeared.map((sig, i) => (
                    <div key={i} className="flex items-center justify-between text-xs text-slate-300 bg-rose-950/30 rounded px-2 py-1">
                      <span>{sig.label}</span>
                      <span className="text-slate-400">{sig.offset_frame != null ? `f${sig.offset_frame}` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {appearDisappear.dominant_shift ? (
              <div className="text-[10px] text-slate-400 border-t border-slate-800 pt-2">
                Dominant shift: {appearDisappear.dominant_shift}
              </div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
