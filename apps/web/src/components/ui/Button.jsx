import React from "react";
import { cn } from "../../lib/utils.js";

const variants = {
  primary:
    "bg-accent text-accent-foreground hover:bg-accent-hover shadow-sm focus-visible:ring-accent",
  secondary:
    "bg-surface text-foreground border border-border hover:bg-surface-subtle focus-visible:ring-ring",
  ghost:
    "text-muted-foreground hover:text-foreground hover:bg-surface-subtle focus-visible:ring-ring",
  danger:
    "bg-danger text-danger-foreground hover:bg-danger/90 shadow-sm focus-visible:ring-danger",
  outline:
    "border border-border bg-transparent hover:bg-surface-subtle text-foreground focus-visible:ring-ring",
};

const sizes = {
  sm: "h-8 px-2.5 text-xs rounded-md",
  md: "h-9 px-3.5 text-sm rounded-lg",
  lg: "h-10 px-4 text-sm font-medium rounded-lg",
  icon: "h-8 w-8 p-0 rounded-md flex items-center justify-center",
};

export const Button = React.forwardRef(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

