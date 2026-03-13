"use client";
import { useState } from "react";

interface Result {
  repo: string;
  originality_score: number;
  code_similarity: number;
  idea_novelty: number;
  verdict: string;
  flagged_files: string[];
  similar_projects: string[];
  strengths: string[];
  concerns: string[];
  files_scanned: number;
  raw_similar: { name: string; url: string; description: string; stars: number }[];
  error?: string;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  const stages = [
    "Fetching repository files...",
    "Scanning code structure...",
    "Searching similar projects on GitHub...",
    "Running AI originality analysis...",
    "Generating verdict...",
  ];

  const analyse = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);
    let i = 0;
    setStage(stages[0]);
    const interval = setInterval(() => {
      i = (i + 1) % stages.length;
      setStage(stages[i]);
    }, 2500);
    try {
      const res = await fetch("http://127.0.0.1:8001/analyse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url }),
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setResult({ error: "Cannot reach backend. Make sure uvicorn is running on port 8000." } as Result);
    } finally {
      clearInterval(interval);
      setLoading(false);
      setStage("");
    }
  };

  const color = (v: number) => v >= 70 ? "#1D9E75" : v >= 40 ? "#BA7517" : "#D85A30";
  const label = (v: number) => v >= 70 ? "Original" : v >= 40 ? "Partially Original" : "Likely Plagiarised";

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#fff", fontFamily: "sans-serif" }}>
      <div style={{ maxWidth: 780, margin: "0 auto", padding: "48px 20px" }}>

        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div style={{ fontSize: 11, fontWeight: 500, letterSpacing: ".15em", color: "#888", textTransform: "uppercase", marginBottom: 16 }}>Hackathon Tool</div>
          <div style={{ fontSize: 42, fontWeight: 600, marginBottom: 12, background: "linear-gradient(135deg, #fff 0%, #888 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>OriginalityAI</div>
          <div style={{ fontSize: 16, color: "#666", maxWidth: 420, margin: "0 auto" }}>Paste any GitHub repo URL to instantly check how original the project is</div>
        </div>

        <div style={{ display: "flex", gap: 10, marginBottom: 48 }}>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && analyse()}
            placeholder="https://github.com/username/repo"
            style={{ flex: 1, padding: "14px 18px", fontSize: 14, borderRadius: 10, border: "1px solid #333", background: "#111", color: "#fff", outline: "none" }}
          />
          <button
            onClick={analyse}
            disabled={loading}
            style={{ background: loading ? "#333" : "#fff", color: loading ? "#666" : "#000", border: "none", borderRadius: 10, padding: "14px 28px", fontSize: 14, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", whiteSpace: "nowrap" }}
          >
            {loading ? "Scanning..." : "Analyse →"}
          </button>
        </div>

        {loading && (
          <div style={{ background: "#111", border: "1px solid #222", borderRadius: 12, padding: 24, marginBottom: 24, textAlign: "center" }}>
            <div style={{ fontSize: 13, color: "#888", marginBottom: 16 }}>{stage}</div>
            <div style={{ height: 2, background: "#222", borderRadius: 99, overflow: "hidden" }}>
              <div style={{ height: "100%", background: "#fff", borderRadius: 99, animation: "scan 2s ease-in-out infinite" }} />
            </div>
            <style>{`@keyframes scan { 0%{width:0%;margin-left:0} 50%{width:50%;margin-left:25%} 100%{width:0%;margin-left:100%} }`}</style>
          </div>
        )}

        {result?.error && (
          <div style={{ background: "#1a0000", border: "1px solid #440000", borderRadius: 12, padding: 16, color: "#ff6b6b", fontSize: 14 }}>
            {result.error}
          </div>
        )}

        {result && !result.error && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            <div style={{ background: "#111", border: "1px solid #222", borderRadius: 16, padding: 32, textAlign: "center" }}>
              <div style={{ fontSize: 12, color: "#555", marginBottom: 8 }}>{result.repo} · {result.files_scanned} files scanned</div>
              <div style={{ fontSize: 80, fontWeight: 700, color: color(result.originality_score), lineHeight: 1 }}>{result.originality_score}</div>
              <div style={{ fontSize: 13, color: "#555", margin: "4px 0 12px" }}>/ 100</div>
              <div style={{ display: "inline-block", background: color(result.originality_score) + "22", color: color(result.originality_score), fontSize: 12, fontWeight: 600, padding: "6px 16px", borderRadius: 99, border: `1px solid ${color(result.originality_score)}44` }}>
                {label(result.originality_score)}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0,1fr))", gap: 12 }}>
              {[
                { label: "Originality", value: result.originality_score },
                { label: "Code uniqueness", value: 100 - result.code_similarity },
                { label: "Idea novelty", value: result.idea_novelty },
              ].map((s) => (
                <div key={s.label} style={{ background: "#111", border: "1px solid #222", borderRadius: 12, padding: 20, textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "#555", marginBottom: 8, textTransform: "uppercase", letterSpacing: ".08em" }}>{s.label}</div>
                <div style={{ fontSize: 32, fontWeight: 600, color: color(s.value) }}>{isNaN(s.value) ? 0 : s.value}</div>
                  <div style={{ height: 3, background: "#222", borderRadius: 99, marginTop: 10 }}>
                    <div style={{ height: 3, borderRadius: 99, background: color(s.value), width: `${s.value}%`, transition: "width 1s ease" }} />
                  </div>
                </div>
              ))}
            </div>

            <div style={{ background: "#0d0d1f", border: "1px solid #1a1a4f", borderRadius: 12, padding: 24 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#6666ff", marginBottom: 10, textTransform: "uppercase", letterSpacing: ".08em" }}>AI Verdict</div>
              <div style={{ fontSize: 15, color: "#ccc", lineHeight: 1.7 }}>{result.verdict}</div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 12 }}>
              {result.strengths?.length > 0 && (
                <div style={{ background: "#111", border: "1px solid #222", borderRadius: 12, padding: 20 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#1D9E75", marginBottom: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>Strengths</div>
                  {result.strengths.map((s, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, marginBottom: 8 }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#1D9E75", marginTop: 6, flexShrink: 0 }} />
                      <div style={{ fontSize: 13, color: "#999", lineHeight: 1.5 }}>{s}</div>
                    </div>
                  ))}
                </div>
              )}
              {result.concerns?.length > 0 && (
                <div style={{ background: "#111", border: "1px solid #222", borderRadius: 12, padding: 20 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#D85A30", marginBottom: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>Concerns</div>
                  {result.concerns.map((c, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, marginBottom: 8 }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#D85A30", marginTop: 6, flexShrink: 0 }} />
                      <div style={{ fontSize: 13, color: "#999", lineHeight: 1.5 }}>{c}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {result.flagged_files?.length > 0 && (
              <div style={{ background: "#111", border: "1px solid #222", borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#D85A30", marginBottom: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>Flagged files</div>
                {result.flagged_files.map((f, i) => (
                  <div key={i} style={{ background: "#1a0a00", borderRadius: 8, padding: "8px 12px", marginBottom: 6, fontSize: 12, color: "#ff8855", fontFamily: "monospace" }}>{f}</div>
                ))}
              </div>
            )}

            {result.raw_similar?.length > 0 && (
              <div style={{ background: "#111", border: "1px solid #222", borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#888", marginBottom: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>Similar projects found</div>
                {result.raw_similar.map((r, i) => (
                  <div key={i} style={{ padding: "10px 0", borderBottom: i < result.raw_similar.length - 1 ? "1px solid #1a1a1a" : "none" }}>
                    <a href={r.url} target="_blank" rel="noreferrer" style={{ fontSize: 13, fontWeight: 600, color: "#6699ff", textDecoration: "none" }}>{r.name}</a>
                    <span style={{ fontSize: 11, color: "#444", marginLeft: 8 }}>★ {r.stars}</span>
                    <div style={{ fontSize: 12, color: "#555", marginTop: 3 }}>{r.description}</div>
                  </div>
                ))}
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}
