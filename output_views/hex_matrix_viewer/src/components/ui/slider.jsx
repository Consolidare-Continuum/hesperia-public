import React from "react";

/** Radix-like API: value is number[] length 1 */
export function Slider({ value, min, max, step = 1, onValueChange, className = "" }) {
  const v = Array.isArray(value) ? value[0] : value;
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={v}
      onChange={(e) => onValueChange([Number(e.target.value)])}
      className={`w-full accent-slate-300 ${className}`}
    />
  );
}
