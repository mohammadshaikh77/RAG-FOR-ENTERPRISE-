import React from "react";
import {
  Building2,
  Laptop,
  Moon,
  Sun,
  User,
} from "lucide-react";
import { Badge } from "../components/ui/Badge.jsx";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";

export function SettingsPage() {
  const { user, organization } = useAuth();
  const { theme, setTheme } = useTheme();

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Workspace Settings
        </h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Manage your organization workspace, user profile, and display preferences.
        </p>
      </div>

      {/* User Profile Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-accent" />
            <CardTitle>User Profile</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="flex items-center justify-between py-1 border-b border-border/40">
            <span className="text-muted-foreground">Full Name</span>
            <span className="font-semibold text-foreground">
              {user?.full_name || "—"}
            </span>
          </div>

          <div className="flex items-center justify-between py-1 border-b border-border/40">
            <span className="text-muted-foreground">Email Address</span>
            <span className="font-mono text-foreground">{user?.email || "—"}</span>
          </div>

          <div className="flex items-center justify-between py-1">
            <span className="text-muted-foreground">Account Role</span>
            <Badge variant="accent" className="uppercase font-mono text-[10px]">
              {user?.role || "member"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Organization Workspace Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-accent" />
            <CardTitle>Tenant Organization</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="flex items-center justify-between py-1 border-b border-border/40">
            <span className="text-muted-foreground">Organization Name</span>
            <span className="font-semibold text-foreground">
              {organization?.name || "—"}
            </span>
          </div>

          <div className="flex items-center justify-between py-1 border-b border-border/40">
            <span className="text-muted-foreground">Workspace Slug</span>
            <span className="font-mono text-foreground">
              {organization?.slug || "—"}
            </span>
          </div>

          <div className="flex items-center justify-between py-1">
            <span className="text-muted-foreground">Tenant ID</span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {organization?.id || "—"}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Display & Theme Preferences */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sun className="h-4 w-4 text-accent" />
            <CardTitle>Appearance & Theme</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Select your preferred interface color theme.
          </p>

          <div className="grid grid-cols-3 gap-2.5 pt-1">
            <button
              type="button"
              onClick={() => setTheme("light")}
              className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-medium transition-all ${
                theme === "light"
                  ? "border-accent bg-accent-subtle text-accent font-semibold ring-2 ring-accent/20"
                  : "border-border bg-surface text-muted-foreground hover:bg-surface-subtle"
              }`}
            >
              <Sun className="h-4 w-4 mb-1.5" />
              <span>Light</span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("dark")}
              className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-medium transition-all ${
                theme === "dark"
                  ? "border-accent bg-accent-subtle text-accent font-semibold ring-2 ring-accent/20"
                  : "border-border bg-surface text-muted-foreground hover:bg-surface-subtle"
              }`}
            >
              <Moon className="h-4 w-4 mb-1.5" />
              <span>Dark</span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("system")}
              className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-medium transition-all ${
                theme === "system"
                  ? "border-accent bg-accent-subtle text-accent font-semibold ring-2 ring-accent/20"
                  : "border-border bg-surface text-muted-foreground hover:bg-surface-subtle"
              }`}
            >
              <Laptop className="h-4 w-4 mb-1.5" />
              <span>System</span>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

