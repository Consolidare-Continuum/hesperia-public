import React from "react";

export function Card({ children, className = "" }) {
  return <div className={className}>{children}</div>;
}

export function CardHeader({ children, className = "" }) {
  return <div className={`px-6 pt-6 ${className}`}>{children}</div>;
}

export function CardTitle({ children, className = "" }) {
  return <div className={`font-semibold leading-none tracking-tight ${className}`}>{children}</div>;
}

export function CardContent({ children, className = "" }) {
  return <div className={`p-6 pt-0 ${className}`}>{children}</div>;
}
