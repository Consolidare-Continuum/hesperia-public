import React from "react";

export function Button({ children, className = "", variant = "default", onClick, type = "button" }) {
  const base =
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:pointer-events-none disabled:opacity-50 px-4 py-2";
  const styles =
    variant === "secondary"
      ? "bg-slate-700 text-slate-100 hover:bg-slate-600 border border-slate-600"
      : "bg-slate-200 text-slate-900 hover:bg-white";
  return (
    <button type={type} className={`${base} ${styles} ${className}`} onClick={onClick}>
      {children}
    </button>
  );
}
