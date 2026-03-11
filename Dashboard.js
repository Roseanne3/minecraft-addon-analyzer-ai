import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import ScoreCard from "../components/ScoreCard";
import { ErrorDistributionChart, FileTypesChart, SeverityChart } from "../components/ChartPanel";
import FixPanel from "../components/FixPanel";

const API = "http://localhost:8000";

const REPORT_LABELS = {
  manifest: "Manifest", json: "JSON", behavior: "Behavior Pack",
  resource: "Resource Pack", dependency: "Dependency",
  performance: "Performance", ai: "AI Analysis", structure: "Structure",
};

const SEV_ORDER = { error: 0, warning: 1, info: 2 };

function StatCard({ label, value, color = "var(--text)", sub }) {
  return (
    <div className="mc-card" style={{ padding: "1rem", textAlign: "center" }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: "1.75rem", color, fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>{label}</div>
      {sub && <div style={{ fontSize: "0.6rem", color: "var(--text-muted)", marginTop: "0.1rem" }}>{sub}</div>}
    </div>
  );
}

function IssueRow({ issue }) {
  const [expanded, setExpanded] = useState(false);
  const sevColor = { error: "var(--red)", warning: "var(--gold)", info: "var(--blue)" };
  const badgeClass = { error: "badge-error", warning: "badge-warning", info: "badge-info" };

  return (
    <div style={{
      borderBottom: "1px solid var(--border)",
      background: expanded ? "#ffffff06" : "none",
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex", alignItems: "flex-start", gap: "0.75rem",
          padding: "0.6rem 1rem", cursor: "pointer",
        }}
        onMouseEnter={e => e.currentTarget.style.background = "#ffffff08"}
        onMouseLeave={e => e.currentTarget.style.background = expanded ? "#ffffff06" : "none"}
      >
        <span className={`mc-badge ${badgeClass[issue.severity]}`} style={{ flexShrink: 0, marginTop: "1px" }}>
          {issue.severity.toUpperCase()}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text)", lineHeight: 1.5 }}>{issue.message}</div>
          {issue.file_path && (
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginTop: "0.2rem", fontFamily: "var(--font-mono)" }}>
              📄 {issue.file_path}
            </div>
          )}
        </div>
        {issue.auto_fixable && (
          <span style={{
            flexShrink: 0, fontSize: "0.6rem", color: "var(--accent)",
            border: "1px solid var(--accent-dim)", padding: "0.1rem 0.4rem",
          }}>AUTO-FIX</span>
        )}
        {issue.fixed && (
          <span style={{
            flexShrink: 0, fontSize: "0.6rem", color: "#00cc60",
            border: "1px solid #00cc6044", padding: "0.1rem 0.4rem",
          }}>FIXED ✓</span>
        )}
        <span style={{ color: "var(--text-muted)", fontSize: "0.7rem", flexShrink: 0 }}>
          {expanded ? "▾" : "▸"}
        </span>
      </div>

      {expanded && issue.fix_suggestion && (
        <div style={{
          padding: "0.5rem 1rem 0.75rem 3.5rem",
          fontSize: "0.72rem", color: "var(--text-muted)", lineHeight: 1.6,
          borderTop: "1px solid var(--border)", background: "#0a0a18",
        }}>
          <span style={{ color: "var(--accent)", fontWeight: 600 }}>💡 Fix: </span>
          {issue.fix_suggestion}
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { addonId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    axios.get(`${API}/addon/${addonId}`)
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => { setError("Failed to load addon data"); setLoading(false); });
  }, [addonId]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh", gap: "1rem" }}>
      <div className="spinner" style={{ width: "32px", height: "32px" }} />
      <span style={{ fontFamily: "var(--font-display)", fontSize: "0.8rem", color: "var(--text-muted)" }}>
        LOADING ANALYSIS...
      </span>
    </div>
  );

  if (error) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh", gap: "1rem" }}>
      <div style={{ color: "var(--red)", fontSize: "2rem" }}>⚠</div>
      <div style={{ color: "var(--red)", fontFamily: "var(--font-display)", fontSize: "0.8rem" }}>{error}</div>
      <Link to="/" className="mc-btn">← BACK TO UPLOAD</Link>
    </div>
  );

  const { stats, reports_by_type, files, score, filename } = data;

  // Compile all issues
  const allIssues = Object.values(reports_by_type || {}).flat();
  const tabIssues = activeTab === "all" ? allIssues : (reports_by_type[activeTab] || []);
  const filteredIssues = severityFilter === "all"
    ? tabIssues
    : tabIssues.filter(i => i.severity === severityFilter);
  const sortedIssues = [...filteredIssues].sort((a, b) => (SEV_ORDER[a.severity] || 3) - (SEV_ORDER[b.severity] || 3));

  const tabs = ["all", ...Object.keys(reports_by_type || {})];

  return (
    <div style={{ maxWidth: "1400px", margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "2rem", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <Link to="/" style={{ fontSize: "0.65rem", color: "var(--text-muted)", textDecoration: "none", display: "flex", alignItems: "center", gap: "0.3rem", marginBottom: "0.5rem" }}>
            ← UPLOAD NEW ADDON
          </Link>
          <h1 style={{
            fontFamily: "var(--font-display)", fontSize: "clamp(1rem, 2.5vw, 1.4rem)",
            color: "var(--text)", letterSpacing: "0.05em",
          }}>
            {filename}
          </h1>
          <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
            ID #{addonId} · {new Date(data.upload_time).toLocaleString()}
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={() => navigate(`/viewer/${addonId}`)} className="mc-btn" style={{ fontSize: "0.7rem" }}>
            🗂 File Explorer
          </button>
        </div>
      </div>

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "1.5rem", alignItems: "start" }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <ScoreCard score={score} />
          <FixPanel addonId={addonId} stats={stats} />

          {/* Stat cards */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <StatCard label="Files Scanned" value={stats.files_scanned} color="var(--blue)" />
            <StatCard label="Total Issues" value={stats.total_issues} color="var(--text)" />
            <StatCard label="Errors" value={stats.errors} color="var(--red)" />
            <StatCard label="Warnings" value={stats.warnings} color="var(--gold)" />
          </div>

          {/* Charts */}
          <div className="mc-card" style={{ padding: "1rem" }}>
            <div className="section-label" style={{ marginBottom: "0.75rem" }}>Error Distribution</div>
            <ErrorDistributionChart stats={stats} />
          </div>

          <div className="mc-card" style={{ padding: "1rem" }}>
            <div className="section-label" style={{ marginBottom: "0.75rem" }}>Severity Breakdown</div>
            <SeverityChart stats={stats} />
          </div>

          {stats.file_types && Object.keys(stats.file_types).length > 0 && (
            <div className="mc-card" style={{ padding: "1rem" }}>
              <div className="section-label" style={{ marginBottom: "0.75rem" }}>File Types</div>
              <FileTypesChart fileTypes={stats.file_types} />
            </div>
          )}
        </div>

        {/* Right column - Issues */}
        <div>
          {/* Tabs */}
          <div style={{
            display: "flex", gap: "0.25rem", flexWrap: "wrap",
            marginBottom: "1rem", borderBottom: "1px solid var(--border)", paddingBottom: "0.5rem",
          }}>
            {tabs.map(tab => {
              const count = tab === "all" ? allIssues.length : (reports_by_type[tab]?.length || 0);
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    background: activeTab === tab ? "#00ff7f20" : "none",
                    border: activeTab === tab ? "1px solid var(--accent-dim)" : "1px solid var(--border)",
                    color: activeTab === tab ? "var(--accent)" : "var(--text-muted)",
                    fontFamily: "var(--font-mono)", fontSize: "0.68rem",
                    padding: "0.3rem 0.75rem", cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  {REPORT_LABELS[tab] || tab.charAt(0).toUpperCase() + tab.slice(1)}
                  <span style={{ marginLeft: "0.4rem", opacity: 0.7 }}>({count})</span>
                </button>
              );
            })}
          </div>

          {/* Severity filter */}
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", alignItems: "center" }}>
            <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>Filter:</span>
            {["all", "error", "warning", "info"].map(sev => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                style={{
                  background: severityFilter === sev ? "#ffffff15" : "none",
                  border: "1px solid var(--border)",
                  color: sev === "error" ? "var(--red)" : sev === "warning" ? "var(--gold)" : sev === "info" ? "var(--blue)" : "var(--text-muted)",
                  fontFamily: "var(--font-mono)", fontSize: "0.65rem",
                  padding: "0.2rem 0.6rem", cursor: "pointer",
                  textTransform: "uppercase",
                }}
              >
                {sev}
              </button>
            ))}
            <span style={{ marginLeft: "auto", fontSize: "0.65rem", color: "var(--text-muted)" }}>
              {sortedIssues.length} shown
            </span>
          </div>

          {/* Issues list */}
          <div className="mc-card" style={{ overflow: "hidden" }}>
            {sortedIssues.length === 0 ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                {allIssues.length === 0 ? "🎉 No issues found! Addon looks great." : "No issues match the current filter."}
              </div>
            ) : (
              sortedIssues.map((issue, i) => <IssueRow key={i} issue={issue} />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
