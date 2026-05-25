"""
Performance Dashboard Generator for The Daily Audit
Generates a self-contained HTML dashboard from analytics_log.jsonl + YouTube performance data.

Usage:
    python performance_dashboard.py                 # Generate to default path
    python performance_dashboard.py --output report.html
    python performance_dashboard.py --serve          # Generate + start local server
"""
import os
import json
import argparse
import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


# ── Data Layer ────────────────────────────────────────────────────────────────

def load_log(log_path: str) -> List[Dict]:
    """Load all entries from analytics_log.jsonl."""
    if not os.path.exists(log_path):
        return []
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def compute_dashboard_data(entries: List[Dict]) -> Dict:
    """Extract all metrics needed for the dashboard from raw log entries."""
    now = datetime.datetime.utcnow()

    # ── Basics ──
    total_videos = len(entries)
    with_performance = [e for e in entries if e.get("performance") and "error" not in e.get("performance", {})]
    total_views = sum(int(e.get("performance", {}).get("views", 0)) for e in with_performance)

    # ── Style Performance ──
    style_data: Dict[str, List[float]] = {}
    style_views: Dict[str, int] = {}
    style_count: Dict[str, int] = {}
    for e in with_performance:
        style = e.get("style_preset", "unknown")
        ret = safe_float(e.get("performance", {}).get("average_view_percentage"))
        if ret > 0:
            style_data.setdefault(style, []).append(ret)
            style_count[style] = style_count.get(style, 0) + 1
            style_views[style] = style_views.get(style, 0) + int(e["performance"].get("views", 0))

    style_perf = [
        {"label": s, "retention": round(sum(v)/len(v), 1),
         "videos": style_count[s], "views": style_views.get(s, 0)}
        for s, v in sorted(style_data.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
    ]

    # ── Category Performance ──
    cat_data: Dict[str, List[float]] = {}
    cat_views: Dict[str, int] = {}
    cat_count: Dict[str, int] = {}
    for e in with_performance:
        cat = e.get("category", "unknown")
        ret = safe_float(e.get("performance", {}).get("average_view_percentage"))
        if ret > 0:
            cat_data.setdefault(cat, []).append(ret)
            cat_count[cat] = cat_count.get(cat, 0) + 1
            cat_views[cat] = cat_views.get(cat, 0) + int(e["performance"].get("views", 0))

    cat_perf = [
        {"label": c, "retention": round(sum(v)/len(v), 1),
         "videos": cat_count[c], "views": cat_views.get(c, 0)}
        for c, v in sorted(cat_data.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
    ]

    # ── Transition Performance ──
    trans_data: Dict[str, List[float]] = {}
    trans_count: Dict[str, int] = {}
    for e in with_performance:
        trans = e.get("transition_type", "unknown")
        ret = safe_float(e.get("performance", {}).get("average_view_percentage"))
        if ret > 0:
            trans_data.setdefault(trans, []).append(ret)
            trans_count[trans] = trans_count.get(trans, 0) + 1

    trans_perf = [
        {"label": t, "retention": round(sum(v)/len(v), 1), "videos": trans_count[t]}
        for t, v in sorted(trans_data.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
    ]

    # ── Trend: Retention over time (by upload date, rolling 7-video average) ──
    trend_points = []
    for e in with_performance:
        ret = safe_float(e.get("performance", {}).get("average_view_percentage"))
        views = int(e.get("performance", {}).get("views", 0))
        uploaded = e.get("uploaded_at", "")
        topic = e.get("topic", "?")
        style = e.get("style_preset", "?")
        if ret > 0 and uploaded:
            trend_points.append({
                "date": uploaded[:10],
                "retention": ret,
                "views": views,
                "topic": topic,
                "style": style,
            })

    # Sort by date
    trend_points.sort(key=lambda x: x["date"])

    # Rolling average (window=7)
    rolling = []
    window = min(7, max(1, len(trend_points) // 2))
    for i in range(len(trend_points)):
        start = max(0, i - window + 1)
        chunk = [p["retention"] for p in trend_points[start:i+1]]
        avg = round(sum(chunk) / len(chunk), 1) if chunk else 0
        rolling.append({
            "date": trend_points[i]["date"],
            "retention": trend_points[i]["retention"],
            "rolling_avg": avg,
            "views": trend_points[i]["views"],
            "topic": trend_points[i]["topic"],
            "style": trend_points[i]["style"],
        })

    # ── Top / Bottom Topics ──
    topic_list = []
    for e in with_performance:
        ret = safe_float(e.get("performance", {}).get("average_view_percentage"))
        views = int(e.get("performance", {}).get("views", 0))
        if ret > 0:
            topic_list.append({
                "topic": e.get("topic", "?"),
                "category": e.get("category", "?"),
                "retention": ret,
                "views": views,
                "style": e.get("style_preset", "?"),
            })

    topic_list.sort(key=lambda x: x["retention"], reverse=True)
    top_topics = topic_list[:10]
    bottom_topics = topic_list[-10:][::-1]

    # ── Summary Stats ──
    all_retentions = [safe_float(e.get("performance", {}).get("average_view_percentage"))
                      for e in with_performance if safe_float(e.get("performance", {}).get("average_view_percentage")) > 0]
    avg_retention = round(sum(all_retentions) / len(all_retentions), 1) if all_retentions else 0
    max_retention = round(max(all_retentions), 1) if all_retentions else 0
    min_retention = round(min(all_retentions), 1) if all_retentions else 0

    # ── Video Type mix ──
    type_mix = {}
    for e in entries:
        vtype = e.get("format", e.get("video_type", "unknown"))
        type_mix[vtype] = type_mix.get(vtype, 0) + 1

    # ── Production schedule (videos per day) ──
    day_counts = {}
    for e in entries:
        date = (e.get("uploaded_at") or e.get("logged_at", ""))[:10]
        if date:
            day_counts[date] = day_counts.get(date, 0) + 1

    return {
        "total_videos": total_videos,
        "with_performance": len(with_performance),
        "total_views": total_views,
        "avg_retention": avg_retention,
        "max_retention": max_retention,
        "min_retention": min_retention,
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "style_performance": style_perf,
        "category_performance": cat_perf,
        "transition_performance": trans_perf,
        "trend": rolling,
        "top_topics": top_topics,
        "bottom_topics": bottom_topics,
        "type_mix": type_mix,
        "production_schedule": dict(sorted(day_counts.items())),
    }


# ── HTML Template ─────────────────────────────────────────────────────────────

def generate_html(data: Dict) -> str:
    """Generate a self-contained HTML dashboard page."""
    s = data["style_performance"]
    c = data["category_performance"]
    t = data["transition_performance"]
    trend = data["trend"]
    top_t = data["top_topics"]
    bot_t = data["bottom_topics"]
    type_mix = data["type_mix"]
    sched = data["production_schedule"]

    # Serialize data into JS-safe JSON
    import html as h

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Daily Audit — Performance Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0a0a0f; color: #e0e0e0; padding: 24px; }}
h1 {{ font-size: 28px; color: #00f2fe; margin-bottom: 4px; }}
.subtitle {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
.stats-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }}
.stat-card {{ background: #141420; border: 1px solid #2a2a3a; border-radius: 12px;
             padding: 18px 22px; flex: 1; min-width: 140px; }}
.stat-card .value {{ font-size: 32px; font-weight: 700; color: #fff; }}
.stat-card .label {{ font-size: 13px; color: #888; margin-top: 2px; }}
.stat-card .badge {{ font-size: 11px; color: #555; margin-top: 4px; }}
.chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px; }}
.chart-card {{ background: #141420; border: 1px solid #2a2a3a; border-radius: 12px; padding: 20px; }}
.chart-card.full {{ grid-column: 1 / -1; }}
.chart-card h3 {{ font-size: 15px; color: #aaa; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
canvas {{ max-height: 320px; }}
.topic-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.topic-table th {{ text-align: left; padding: 8px 12px; color: #888; border-bottom: 1px solid #2a2a3a;
                  font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
.topic-table td {{ padding: 8px 12px; border-bottom: 1px solid #1a1a2a; }}
.topic-table tr:hover {{ background: #1c1c2e; }}
.ret-bar {{ display: inline-block; height: 6px; border-radius: 3px; margin-right: 8px; vertical-align: middle; }}
.ret-good {{ background: #00f2fe; }}
.ret-mid {{ background: #ffe066; }}
.ret-bad {{ background: #ff4757; }}
.muted {{ color: #666; font-size: 11px; }}
.tag {{ display: inline-block; background: #1a1a2e; color: #888; border-radius: 4px; padding: 1px 6px; font-size: 10px; }}
@media (max-width: 800px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>📊 The Daily Audit</h1>
<div class="subtitle">Performance Dashboard &middot; Generated {data["generated_at"]}</div>

<div class="stats-row">
  <div class="stat-card">
    <div class="value">{data["total_videos"]}</div>
    <div class="label">Total Videos</div>
    <div class="badge">{data["with_performance"]} with performance data</div>
  </div>
  <div class="stat-card">
    <div class="value">{data["total_views"]:,}</div>
    <div class="label">Total Views</div>
  </div>
  <div class="stat-card">
    <div class="value">{data["avg_retention"]}%</div>
    <div class="label">Avg Retention</div>
    <div class="badge">{data["max_retention"]}% max &middot; {data["min_retention"]}% min</div>
  </div>
  <div class="stat-card">
    <div class="value">{len(trend)}</div>
    <div class="label">Videos with Trend</div>
    <div class="badge">{round(data.get("total_views", 0) / max(data["total_videos"], 1)) if data["total_videos"] > 0 else 0} avg views/video</div>
  </div>
</div>

<div class="chart-grid">
  <div class="chart-card">
    <h3>🎨 Style Performance</h3>
    <canvas id="styleChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>📂 Category Performance</h3>
    <canvas id="catChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>🔄 Transition Performance</h3>
    <canvas id="transChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>📦 Video Type Mix</h3>
    <canvas id="typeChart"></canvas>
  </div>
  <div class="chart-card full">
    <h3>📈 Retention Trend ({"7-video" if len(trend) > 6 else "available"} rolling average)</h3>
    <canvas id="trendChart"></canvas>
  </div>
  <div class="chart-card full">
    <h3>🏆 Top Topics by Retention</h3>
    <table class="topic-table">
      <thead><tr><th>#</th><th>Topic</th><th>Category</th><th>Style</th><th>Retention</th><th>Views</th></tr></thead>
      <tbody>
        {"".join(f'<tr><td>{i+1}</td><td>{item["topic"][:55]}</td><td><span class="tag">{item["category"]}</span></td><td><span class="tag">{item["style"]}</span></td><td><span class="ret-bar {"ret-good" if item["retention"] > data["avg_retention"] else "ret-mid"}" style="width:{max(4, item["retention"]*2)}px"></span>{item["retention"]:.1f}%</td><td>{item["views"]:,}</td></tr>' for i, item in enumerate(top_t[:8]))}
      </tbody>
    </table>
  </div>
  <div class="chart-card full">
    <h3>⚠️ Bottom Topics by Retention</h3>
    <table class="topic-table">
      <thead><tr><th>#</th><th>Topic</th><th>Category</th><th>Style</th><th>Retention</th><th>Views</th></tr></thead>
      <tbody>
        {"".join(f'<tr><td>{i+1}</td><td>{item["topic"][:55]}</td><td><span class="tag">{item["category"]}</span></td><td><span class="tag">{item["style"]}</span></td><td><span class="ret-bar {"ret-bad" if item["retention"] < data["avg_retention"] else "ret-mid"}" style="width:{max(4, item["retention"]*2)}px"></span>{item["retention"]:.1f}%</td><td>{item["views"]:,}</td></tr>' for i, item in enumerate(bot_t[:8]))}
      </tbody>
    </table>
  </div>
</div>

<script>
const bg = '#141420', gridColor = '#2a2a3a', textColor = '#aaa';
const chartDefaults = {{
  responsive: true, maintainAspectRatio: true,
  plugins: {{ legend: {{ labels: {{ color: textColor, boxWidth: 12, padding: 12 }} }} }},
  scales: {{
    x: {{ ticks: {{ color: textColor, maxRotation: 45 }}, grid: {{ color: gridColor }} }},
    y: {{ beginAtZero: true, ticks: {{ color: textColor, callback: v => v + '%' }}, grid: {{ color: gridColor }} }}
  }}
}};

// Style Chart
new Chart(document.getElementById('styleChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps([s["label"] for s in s])},
    datasets: [{{
      label: 'Avg Retention %',
      data: {json.dumps([s["retention"] for s in s])},
      backgroundColor: ['#00f2fe', '#ffe066', '#ff6b6b', '#a29bfe', '#55efc4', '#fd79a8', '#fdcb6e'],
      borderRadius: 4,
    }}]
  }},
  options: {{ ...chartDefaults, plugins: {{ ...chartDefaults.plugins, tooltip: {{
    callbacks: {{
      afterLabel: ctx => ctx.raw + '% retention (' + {json.dumps({s["label"]: s["videos"] for s in s})}[ctx.label] + ' videos)'
    }}
  }} }} }}
}});

// Category Chart
new Chart(document.getElementById('catChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps([c["label"] for c in c])},
    datasets: [{{
      label: 'Avg Retention %',
      data: {json.dumps([c["retention"] for c in c])},
      backgroundColor: ['#a29bfe', '#55efc4', '#fdcb6e', '#00f2fe', '#ff6b6b', '#fd79a8', '#74b9ff'],
      borderRadius: 4,
    }}]
  }},
  options: chartDefaults
}});

// Transition Chart
new Chart(document.getElementById('transChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps([t_["label"] for t_ in t])},
    datasets: [{{
      label: 'Avg Retention %',
      data: {json.dumps([t_["retention"] for t_ in t])},
      backgroundColor: ['#55efc4', '#ffe066', '#ff6b6b', '#a29bfe'],
      borderRadius: 4,
    }}]
  }},
  options: chartDefaults
}});

// Video Type Pie
new Chart(document.getElementById('typeChart'), {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(list(type_mix.keys()))},
    datasets: [{{
      data: {json.dumps(list(type_mix.values()))},
      backgroundColor: ['#00f2fe', '#ffe066', '#ff6b6b', '#a29bfe', '#55efc4'],
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: true,
    plugins: {{ legend: {{ position: 'right', labels: {{ color: textColor, boxWidth: 12 }} }} }}
  }}
}});

// Trend Chart
const trendDates = {json.dumps([p["date"] for p in trend])};
const trendRet = {json.dumps([p["retention"] for p in trend])};
const trendRoll = {json.dumps([p["rolling_avg"] for p in trend])};

new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{
    labels: trendDates,
    datasets: [
      {{
        label: 'Per-Video Retention',
        data: trendRet,
        borderColor: '#00f2fe40',
        backgroundColor: '#00f2fe10',
        pointRadius: 3,
        pointBackgroundColor: '#00f2fe',
        borderWidth: 1,
        fill: true,
        tension: 0.3,
      }},
      {{
        label: 'Rolling Avg',
        data: trendRoll,
        borderColor: '#00f2fe',
        borderWidth: 2.5,
        pointRadius: 0,
        tension: 0.4,
      }}
    ]
  }},
  options: {{
    ...chartDefaults,
    plugins: {{ ...chartDefaults.plugins, tooltip: {{
      callbacks: {{
        afterLabel: ctx => {{
          const idx = ctx.dataIndex;
          return {json.dumps([f"{p['topic']} | {p['style']} | {p['views']} views" for p in trend])}[idx];
        }}
      }}
    }} }}
  }}
}});
</script>
</body>
</html>"""


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate performance dashboard")
    parser.add_argument("--output", "-o", default=None,
                        help="Output HTML path (default: database/performance_dashboard.html)")
    parser.add_argument("--serve", action="store_true",
                        help="Start a local HTTP server after generating")
    parser.add_argument("--port", type=int, default=8080, help="Port for --serve")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "database", "analytics_log.jsonl")

    entries = load_log(log_path)
    data = compute_dashboard_data(entries)
    html = generate_html(data)

    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(base_dir, "database", "performance_dashboard.html")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Dashboard] Generated: {output_path}")
    print(f"[Dashboard] {data['total_videos']} videos, "
          f"{data['with_performance']} with performance data, "
          f"{data['total_views']:,} total views")
    print(f"[Dashboard] Avg retention: {data['avg_retention']}% | "
          f"Best: {data['max_retention']}% | Worst: {data['min_retention']}%")

    if args.serve:
        import http.server
        import socketserver
        os.chdir(os.path.dirname(output_path))
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            print(f"[Dashboard] Serving at http://localhost:{args.port}/performance_dashboard.html")
            httpd.serve_forever()


if __name__ == "__main__":
    main()
