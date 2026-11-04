import React from "react";
import { cn } from "../../lib/utils.js";

const variants = {
  default: "bg-surface text-foreground border-border",
  accent: "bg-accent-subtle text-accent border-accent/20",
  success: "bg-success-subtle text-success border-success/20",
  warning: "bg-warning-subtle text-warning border-warning/20",
  danger: "bg-danger-subtle text-danger border-danger/20",
  muted: "bg-muted text-muted-foreground border-transparent",
};

export function Badge({ className, variant = "default", children, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

