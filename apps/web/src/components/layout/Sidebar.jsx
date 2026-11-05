import React from "react";
import { NavLink } from "react-router-dom";
import {
  FileText,
  LogOut,
  MessageSquare,
  Scale,
  Settings,
  ShieldAlert,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";
import { cn } from "../../lib/utils.js";

const NAV_ITEMS = [
  { label: "Ask", path: "/", icon: MessageSquare },
  { label: "Documents", path: "/documents", icon: FileText },
  { label: "How well does Cite work?", path: "/evaluation", icon: Scale },
  { label: "Settings", path: "/settings", icon: Settings },
];

export function Sidebar({ className }) {
  const { user, organization, logout } = useAuth();

  return (
    <aside
      className={cn(
        "flex flex-col w-64 border-r border-border bg-surface shrink-0 select-none",
        className
      )}
    >
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-5 h-14 border-b border-border/60">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-foreground shadow-sm font-bold text-sm tracking-tight">
          Ct
        </div>
        <div className="flex flex-col">
          <span className="font-semibold text-sm tracking-tight leading-none text-foreground">
            Cite
          </span>
          <span className="text-[10px] text-muted-foreground mt-0.5 tracking-wider uppercase font-mono">
            Document Q&A
          </span>
        </div>
      </div>

      {/* Workspace Chip */}
      <div className="px-4 py-3 border-b border-border/40 bg-surface-subtle/50">
        <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
          Workspace
        </div>
        <div className="flex items-center justify-between">
          <span
            className="text-xs font-semibold text-foreground truncate max-w-[150px]"
            title={organization?.name || "Demo Pharma"}
          >
            {organization?.name || "Demo Pharma"}
          </span>
          <span className="h-2 w-2 rounded-full bg-success ring-4 ring-success/20" />
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors group",
                  isActive
                    ? "bg-accent-subtle text-accent font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-surface-subtle"
                )
              }
            >
              <div className="flex items-center gap-2.5">
                <Icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-normal">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* User Footer Profile & Logout */}
      <div className="p-3 border-t border-border/60 bg-surface-subtle/30">
        <div className="flex items-center justify-between gap-2 p-2 rounded-lg hover:bg-surface-subtle transition-colors">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="h-7 w-7 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-xs font-bold text-accent shrink-0">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-medium text-foreground truncate leading-tight">
                {user?.full_name || "User"}
              </span>
              <span className="text-[10px] text-muted-foreground truncate leading-tight">
                {user?.email}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            title="Log out"
            className="p-1.5 rounded text-muted-foreground hover:text-danger hover:bg-danger-subtle transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}

