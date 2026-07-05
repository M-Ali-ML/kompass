"""Dead-simple eval-run dashboard.

A stdlib-only web server (no extra deps) that reads the JSON reports written by
`evals/run.py` and serves one self-contained page that auto-refreshes. It
re-reads `artifacts/` on every poll, so new runs appear on their own.

    cd backend && uv run python -m evals.dashboard      # http://localhost:8420
    uv run python -m evals.dashboard --port 9000

Nothing to build, no frontend toolchain — just run a couple of evals
(`uv run python -m evals.run`) and open the page.
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Kompass Eval Dashboard</title>
<style>
  :root {
    --bg: #0f1115; --panel: #181b22; --line: #262b36; --ink: #e8ebf1;
    --muted: #9aa4b2; --good: #35c46b; --warn: #e8b13a; --bad: #e5484d;
    --accent: #ff7aa8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  header {
    display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
    padding: 16px 24px; border-bottom: 1px solid var(--line); background: var(--panel);
    position: sticky; top: 0; z-index: 5;
  }
  h1 { font-size: 16px; margin: 0; letter-spacing: .2px; }
  h1 span { color: var(--accent); }
  .grow { flex: 1; }
  select, label { font: inherit; color: var(--ink); }
  select {
    background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
    padding: 6px 10px;
  }
  .muted { color: var(--muted); }
  main { padding: 24px; max-width: 1080px; margin: 0 auto; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
  .card {
    background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px;
  }
  .card .k { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .6px; }
  .card .v { font-size: 24px; font-weight: 650; margin-top: 4px; }
  section { margin-top: 28px; }
  section h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .6px; color: var(--muted); margin: 0 0 12px; }
  .row { display: grid; grid-template-columns: 220px 1fr 70px; align-items: center; gap: 12px; margin: 6px 0; }
  .row .name { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar { height: 10px; border-radius: 6px; background: #23272f; overflow: hidden; }
  .bar > i { display: block; height: 100%; border-radius: 6px; }
  .pct { text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .5px; }
  .chip { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11.5px; margin: 2px 4px 2px 0; }
  .chip.ok { background: rgba(53,196,107,.14); color: var(--good); }
  .chip.no { background: rgba(229,72,77,.16); color: var(--bad); }
  .tag { font-size: 11px; color: var(--muted); }
  .trend { display: flex; align-items: flex-end; gap: 6px; height: 90px; padding-top: 8px; }
  .trend .b { width: 26px; background: #23272f; border-radius: 6px 6px 0 0; position: relative; display: flex; align-items: flex-end; }
  .trend .b > i { width: 100%; border-radius: 6px 6px 0 0; }
  .trend .b.sel { outline: 2px solid var(--accent); outline-offset: 2px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; background: var(--good); }
  .dot.stale { background: var(--warn); }
  .err { color: var(--bad); }
  a { color: var(--accent); }
  .empty { color: var(--muted); padding: 40px; text-align: center; }
</style>
</head>
<body>
<header>
  <h1>Kompass <span>Eval</span> Dashboard</h1>
  <label class="muted">Run
    <select id="runSel"></select>
  </label>
  <span class="grow"></span>
  <label class="muted"><input type="checkbox" id="auto" checked /> auto-refresh</label>
  <span class="muted" id="status"><span class="dot" id="dot"></span> <span id="statusText">loading…</span></span>
</header>
<main id="app"><div class="empty">Loading reports…</div></main>

<script>
const $ = (s, r=document) => r.querySelector(s);
let reports = [];
let selected = null;      // timestamp of selected run, or null = latest
let lastSig = "";

function color(rate) {
  if (rate >= 0.999) return "var(--good)";
  if (rate >= 0.9) return "#7bd88a";
  if (rate >= 0.7) return "var(--warn)";
  return "var(--bad)";
}
const pct = (r) => r == null ? "—" : Math.round(r * 100) + "%";

function overall(summary) {
  let p = 0, t = 0;
  for (const c of Object.values(summary.by_category || {})) { p += c.passed; t += c.total; }
  return t ? p / t : null;
}

function bars(obj) {
  const keys = Object.keys(obj).sort();
  return keys.map(k => {
    const r = obj[k];
    return `<div class="row">
      <div class="name" title="${k}">${k}</div>
      <div class="bar"><i style="width:${(r.pass_rate ?? 0)*100}%;background:${color(r.pass_rate ?? 0)}"></i></div>
      <div class="pct">${r.passed}/${r.total} <span class="muted">${pct(r.pass_rate)}</span></div>
    </div>`;
  }).join("");
}

function caseRows(perCase) {
  return perCase.map(c => {
    const chips = Object.entries(c.assertions || {}).map(([n, v]) =>
      `<span class="chip ${v ? "ok" : "no"}">${v ? "✓" : "✗"} ${n}</span>`).join("");
    const errored = c.total === 0;
    return `<tr>
      <td><div>${c.name}</div><div class="tag">${c.category}</div></td>
      <td>${errored ? '<span class="err">no assertions (errored / no plan)</span>' : chips}</td>
      <td class="pct">${errored ? "—" : c.passed + "/" + c.total}</td>
    </tr>`;
  }).join("");
}

function trend(list) {
  // oldest -> newest
  const items = [...list].reverse();
  return items.map(rp => {
    const o = overall(rp.summary) ?? 0;
    const sel = (selected ? rp.timestamp === selected : rp === list[0]) ? " sel" : "";
    return `<div class="b${sel}" title="${rp.timestamp} · ${pct(o)}" data-ts="${rp.timestamp}"
              style="height:${Math.max(6, o*90)}px" onclick="pick('${rp.timestamp}')">
              <i style="height:100%;background:${color(o)}"></i></div>`;
  }).join("");
}

function pick(ts) { selected = ts; render(); }

function currentReport() {
  if (!reports.length) return null;
  if (selected) return reports.find(r => r.timestamp === selected) || reports[0];
  return reports[0]; // newest first
}

function render() {
  const app = $("#app");
  if (!reports.length) { app.innerHTML = '<div class="empty">No reports yet. Run <code>uv run python -m evals.run</code>.</div>'; return; }
  const rp = currentReport();
  const s = rp.summary;
  const o = overall(s);
  const nCases = (s.per_case || []).length;
  const nErr = (s.per_case || []).filter(c => c.total === 0).length;

  app.innerHTML = `
    <div class="cards">
      <div class="card"><div class="k">Overall</div><div class="v" style="color:${color(o ?? 0)}">${pct(o)}</div></div>
      <div class="card"><div class="k">Model</div><div class="v" style="font-size:16px">${rp.model}</div></div>
      <div class="card"><div class="k">Cases</div><div class="v">${nCases}${nErr ? ` <span class="err" style="font-size:14px">(${nErr} errored)</span>` : ""}</div></div>
      <div class="card"><div class="k">Repeat</div><div class="v">${rp.repeat}×</div></div>
      <div class="card"><div class="k">Run</div><div class="v" style="font-size:14px">${rp.timestamp}</div></div>
    </div>

    <section>
      <h2>Overall pass-rate trend (${reports.length} runs)</h2>
      <div class="trend">${trend(reports)}</div>
    </section>

    <section>
      <h2>By category</h2>
      ${bars(s.by_category || {})}
    </section>

    <section>
      <h2>By assertion</h2>
      ${bars(s.by_assertion || {})}
    </section>

    <section>
      <h2>Per case</h2>
      <table>
        <thead><tr><th>Case</th><th>Assertions</th><th>Pass</th></tr></thead>
        <tbody>${caseRows(s.per_case || [])}</tbody>
      </table>
    </section>`;
}

function fillSelect() {
  const sel = $("#runSel");
  const cur = selected || (reports[0] && reports[0].timestamp);
  sel.innerHTML = reports.map((r, i) =>
    `<option value="${r.timestamp}" ${r.timestamp === cur ? "selected" : ""}>${r.timestamp}${i === 0 ? " (latest)" : ""} · ${pct(overall(r.summary))}</option>`
  ).join("");
  sel.onchange = () => pick(sel.value);
}

async function poll() {
  try {
    const res = await fetch("/api/reports", { cache: "no-store" });
    const data = await res.json();
    const sig = JSON.stringify(data.map(r => r.timestamp));
    $("#dot").className = "dot";
    $("#statusText").textContent = "updated " + new Date().toLocaleTimeString();
    if (sig !== lastSig) {
      lastSig = sig;
      const hadNew = reports.length && data.length && data[0].timestamp !== reports[0].timestamp;
      reports = data;
      // Follow the latest run unless the user explicitly picked an older one.
      if (hadNew && (!selected || selected === (reports[1] && reports[1].timestamp))) selected = null;
      fillSelect();
      render();
    }
  } catch (e) {
    $("#dot").className = "dot stale";
    $("#statusText").textContent = "server unreachable";
  }
}

setInterval(() => { if ($("#auto").checked) poll(); }, 3000);
poll();
</script>
</body>
</html>
"""


def _load_reports() -> list[dict]:
    """Newest-first list of parsed reports (with an `overall` convenience)."""
    reports: list[dict] = []
    for path in _ARTIFACTS.glob("eval_report_*.json"):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        data.setdefault("timestamp", path.stem.replace("eval_report_", ""))
        data.setdefault("model", "?")
        data.setdefault("repeat", 1)
        data.setdefault("summary", {})
        data["file"] = path.name
        reports.append(data)
    reports.sort(key=lambda r: r["timestamp"], reverse=True)
    return reports


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/reports"):
            body = json.dumps(_load_reports()).encode()
            self._send(200, body, "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *args) -> None:  # keep the console quiet
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Kompass eval dashboard.")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-open", action="store_true", help="Don't open a browser.")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    n = len(_load_reports())
    print(f"Kompass eval dashboard → {url}  ({n} report(s) in {_ARTIFACTS})")
    print("Reading artifacts/eval_report_*.json — new runs appear automatically. Ctrl-C to stop.")
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        server.shutdown()


if __name__ == "__main__":
    main()
