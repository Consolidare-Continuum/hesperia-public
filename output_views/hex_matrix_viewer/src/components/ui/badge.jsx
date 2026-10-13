import React from "react";

export function Badge({ children, className = "", variant = "default" }) {
  const v =
    variant === "secondary"
      ? "border border-slate-600 bg-slate-800 text-slate-100"
      : "border border-transparent bg-slate-700 text-slate-100";
  return <span className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium ${v} ${className}`}>{children}</span>;
}
