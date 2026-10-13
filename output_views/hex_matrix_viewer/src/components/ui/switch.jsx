import React from "react";

export function Switch({ checked, onCheckedChange, className = "" }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onCheckedChange(!checked)}
      className={`relative h-6 w-11 rounded-full border border-slate-600 transition-colors ${checked ? "bg-slate-200" : "bg-slate-800"} ${className}`}
    >
      <span
        className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-slate-950 transition-transform ${checked ? "translate-x-5" : ""}`}
      />
    </button>
  );
}
