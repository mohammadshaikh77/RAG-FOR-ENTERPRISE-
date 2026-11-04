import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, Shield, Sparkles } from "lucide-react";
import { Button } from "../components/ui/Button.jsx";
import { Input } from "../components/ui/Input.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export function AuthPage() {
  const location = useLocation();
  const [isRegister, setIsRegister] = useState(location.pathname === "/register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        if (!orgName || !fullName) {
          throw new Error("All fields are required for registration.");
        }
        const slug = orgName
          .toLowerCase()
          .replace(/[^a-z0-9]/g, "-")
          .replace(/-+/g, "-");

        await register({
          org_name: orgName,
          org_slug: slug,
          full_name: fullName,
          email,
          password,
        });
      } else {
        await login({ email, password });
      }
      navigate("/");
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full bg-background font-sans">
      {/* Left Marketing Split */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 bg-surface border-r border-border relative overflow-hidden">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-accent-foreground font-bold text-base shadow-sm">
            Ct
          </div>
          <div>
            <span className="font-bold text-base tracking-tight text-foreground">
              Cite
            </span>
            <span className="text-xs text-muted-foreground block font-mono">
              Enterprise Agentic RAG Platform
            </span>
          </div>
        </div>

        <div className="space-y-6 max-w-lg my-auto">
          <h2 className="text-3xl font-extrabold tracking-tight text-foreground leading-tight">
            Grounded clinical answers with{" "}
            <span className="text-accent underline decoration-accent/30 underline-offset-4">
              proof of quality
            </span>
            .
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            A production-grade document intelligence platform engineered for
            regulated life sciences and enterprise retrieval. Every claim is
            anchored in verifiable source spans with zero ungrounded guessing.
          </p>

          <div className="space-y-3 pt-2">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-accent shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-semibold text-foreground block">
                  Structure-Aware Clinical Ingestion
                </span>
                <span className="text-muted-foreground">
                  Preserves FDA label clinical hierarchies, boxed warnings, and
                  dosage sections.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-accent shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-semibold text-foreground block">
                  Bounded Tool-Calling Agent
                </span>
                <span className="text-muted-foreground">
                  5 whitelisted tools for hybrid retrieval, section extraction,
                  side-by-side comparison, and safe dosage math.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-accent shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-semibold text-foreground block">
                  Strict Query-Level Multi-Tenancy
                </span>
                <span className="text-muted-foreground">
                  Tenant isolation enforced deep inside pgvector and SQL queries.
                  Zero cross-org data leakage.
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="text-[11px] text-muted-foreground font-mono">
          Demo Domain: US FDA Approved Drug Labels & DailyMed Formulations
        </div>
      </div>

      {/* Right Form Split */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center space-y-1 lg:text-left">
            <div className="lg:hidden flex items-center justify-center gap-2 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-foreground font-bold text-sm">
                Ct
              </div>
              <span className="font-bold text-base text-foreground">Cite</span>
            </div>
            <h3 className="text-xl font-bold tracking-tight text-foreground">
              {isRegister ? "Create organization workspace" : "Welcome back"}
            </h3>
            <p className="text-xs text-muted-foreground">
              {isRegister
                ? "Register a new tenant organization to get started"
                : "Sign in to access your grounded document intelligence"}
            </p>
          </div>

          {/* Toggle Tabs */}
          <div className="flex rounded-lg bg-surface-subtle p-1 border border-border/60 text-xs font-medium">
            <button
              type="button"
              onClick={() => {
                setIsRegister(false);
                setError(null);
              }}
              className={`flex-1 py-1.5 rounded-md transition-colors ${
                !isRegister
                  ? "bg-surface text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Log In
            </button>
            <button
              type="button"
              onClick={() => {
                setIsRegister(true);
                setError(null);
              }}
              className={`flex-1 py-1.5 rounded-md transition-colors ${
                isRegister
                  ? "bg-surface text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Register New Tenant
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-lg border border-danger/30 bg-danger-subtle text-xs text-danger leading-relaxed animate-fade-in">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-foreground">
                    Organization Name
                  </label>
                  <Input
                    placeholder="e.g., Pfizer Therapeutics"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-foreground">
                    Your Full Name
                  </label>
                  <Input
                    placeholder="e.g., Dr. Jane Smith"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>
              </>
            )}

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">
                Email Address
              </label>
              <Input
                type="email"
                placeholder="name@organization.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">
                Password
              </label>
              <Input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <Button
              type="submit"
              isLoading={loading}
              className="w-full text-xs font-semibold h-10 mt-2"
            >
              {isRegister ? "Create Tenant & Account" : "Sign In"}
            </Button>
          </form>

          <div className="p-3 rounded-lg border border-border/80 bg-surface-subtle/50 text-[11px] text-muted-foreground text-center">
            Zero-cost open source demo · Seeded with 42 real FDA clinical labels
          </div>
        </div>
      </div>
    </div>
  );
}

