import html
import os
import webbrowser

OUT_DIR = "out"

_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Strava Dashboard</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; background: #14161a; color: #e8e8e8; }
  nav { display: flex; gap: 4px; padding: 10px 16px; background: #1d2026; border-bottom: 1px solid #2a2e36; position: sticky; top: 0; z-index: 10; flex-wrap: wrap; }
  .tab-btn { background: transparent; border: none; color: #b7bcc6; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
  .tab-btn:hover { background: #262a32; color: #fff; }
  .tab-btn.active { background: #fc5200; color: #fff; font-weight: 600; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .tab-panel.padded { padding: 16px; }
  .map-frame { width: 100%; height: calc(100vh - 57px); border: 0; display: block; }
  table { border-collapse: collapse; width: 100%; max-width: 900px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #2a2e36; }
  th { color: #9aa0ab; font-weight: 600; }
  a { color: #ff7433; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .block { margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #2a2e36; }
  .block h3 { margin-bottom: 4px; }
  .bars { max-width: 900px; }
  .bar-row { margin-bottom: 18px; }
  .bar-label { display: inline-block; width: 50px; font-weight: 600; }
  .bar-track { display: inline-block; width: calc(100% - 60px); height: 10px; background: #262a32; border-radius: 5px; vertical-align: middle; overflow: hidden; }
  .bar-fill { height: 100%; background: #fc5200; }
  .bar-value { display: block; margin-top: 4px; margin-left: 58px; color: #b7bcc6; font-size: 13px; }
  .bar-detail { margin-left: 58px; color: #6f7581; font-size: 12px; }
  .empty { color: #9aa0ab; }
</style>
</head>
<body>
<nav>__NAV__</nav>
__PANELS__
<script>
function showTab(index) {
  document.querySelectorAll(".tab-btn").forEach(function (btn, i) {
    btn.classList.toggle("active", i === index);
  });
  document.querySelectorAll(".tab-panel").forEach(function (panel, i) {
    panel.classList.toggle("active", i === index);
  });
}

// Keep pan/zoom in sync across map tabs: each map iframe posts its view on
// move, we remember the latest one and relay it to every other map (and to
// any map that just finished loading), so switching tabs keeps your place.
var lastMapView = null;
window.addEventListener("message", function (e) {
  var data = e.data;
  if (!data || data.source !== "strava-map") return;

  if (data.type === "view") {
    lastMapView = { center: data.center, zoom: data.zoom };
    document.querySelectorAll(".map-frame").forEach(function (frame) {
      if (frame.contentWindow !== e.source) {
        frame.contentWindow.postMessage({ source: "strava-dashboard", center: lastMapView.center, zoom: lastMapView.zoom }, "*");
      }
    });
  } else if (data.type === "ready" && lastMapView) {
    e.source.postMessage({ source: "strava-dashboard", center: lastMapView.center, zoom: lastMapView.zoom }, "*");
  }
});
</script>
</body>
</html>
"""


def _format_duration(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return "{0}:{1:02d}:{2:02d}".format(hours, minutes, secs)
    return "{0}:{1:02d}".format(minutes, secs)


def _map_tab(filename):
    return '<iframe class="map-frame" src="{0}" loading="lazy"></iframe>'.format(html.escape(filename))


def _segments_tab(segment_stats):
    if not segment_stats:
        return '<div class="padded"><p class="empty">No segment data in cache yet. Run with --refresh to fetch segment efforts for cached activities.</p></div>'

    rows = []
    for rank, (segment_id, info) in enumerate(segment_stats, start=1):
        distance_km = (info["distance"] or 0) / 1000
        pr = _format_duration(info["best_time"])
        date = info["best_date"][:10] if info["best_date"] else "-"
        rows.append(
            '<tr><td>{0}</td><td><a href="https://www.strava.com/segments/{1}" target="_blank">{2}</a></td>'
            "<td>{3}</td><td>{4:.1f} km</td><td>{5}</td><td>{6}</td></tr>".format(
                rank, segment_id, html.escape(info["name"] or "?"), info["count"], distance_km, pr, date
            )
        )
    return (
        '<div class="padded"><table><thead><tr><th>#</th><th>Segment</th><th>Attempts</th>'
        "<th>Distance</th><th>PR</th><th>PR date</th></tr></thead><tbody>{0}</tbody></table></div>".format(
            "".join(rows)
        )
    )


def _training_blocks_tab(training_blocks):
    if not training_blocks:
        return '<div class="padded"><p class="empty">No races found (no activity with a \'Race\' workout type).</p></div>'

    sections = []
    for block in training_blocks:
        race = block["race"]
        acts = block["activities"]
        total_km = sum((a.distance or 0) for a in acts) / 1000
        span_days = (race.start_date - acts[0].start_date).days
        activity_rows = "".join(
            "<tr><td>{0}</td><td>{1}</td><td>{2:.1f} km</td></tr>".format(
                a.start_date.date(), html.escape(a.name or "?"), (a.distance or 0) / 1000
            )
            for a in acts
        )
        sections.append(
            '<div class="block"><h3>{0} &mdash; {1}</h3><p>{2} activities over {3} days, {4:.1f} km total</p>'
            "<table><thead><tr><th>Date</th><th>Activity</th><th>Distance</th></tr></thead>"
            "<tbody>{5}</tbody></table></div>".format(
                html.escape(race.name or "?"), race.start_date.date(), len(acts), span_days, total_km, activity_rows
            )
        )
    return '<div class="padded">{0}</div>'.format("".join(sections))


def _stats_tab(yearly_summary):
    if not yearly_summary:
        return '<div class="padded"><p class="empty">No cached activities to summarize yet.</p></div>'

    max_km = max(data["distance_km"] for data in yearly_summary.values()) or 1
    bars = []
    for year in sorted(yearly_summary.keys(), reverse=True):
        data = yearly_summary[year]
        pct = (data["distance_km"] / max_km) * 100
        type_breakdown = ", ".join(
            "{0}: {1:.0f} km".format(t, d["distance_km"])
            for t, d in sorted(data["by_type"].items(), key=lambda kv: kv[1]["distance_km"], reverse=True)
        )
        bars.append(
            '<div class="bar-row"><span class="bar-label">{0}</span>'
            '<div class="bar-track"><div class="bar-fill" style="width:{1:.1f}%"></div></div>'
            "<span class=\"bar-value\">{2:.0f} km &middot; {3:.0f} h &middot; {4} activities</span>"
            '<div class="bar-detail">{5}</div></div>'.format(
                year, pct, data["distance_km"], data["moving_time_hours"], data["count"], html.escape(type_breakdown)
            )
        )
    return '<div class="padded"><div class="bars">{0}</div></div>'.format("".join(bars))


def build_dashboard(maps=None, segment_stats=None, training_blocks=None, yearly_summary=None, open_browser=True):
    """Assemble every requested section into a single tabbed HTML page."""
    tabs = []

    for title, path in (maps or {}).items():
        if path:
            tabs.append((title, _map_tab(os.path.basename(path))))

    if segment_stats is not None:
        tabs.append(("Segments", _segments_tab(segment_stats)))

    if training_blocks is not None:
        tabs.append(("Training Blocks", _training_blocks_tab(training_blocks)))

    if yearly_summary is not None:
        tabs.append(("Stats", _stats_tab(yearly_summary)))

    if not tabs:
        return None

    nav = "".join(
        '<button class="tab-btn{0}" onclick="showTab({1})">{2}</button>'.format(
            " active" if i == 0 else "", i, html.escape(title)
        )
        for i, (title, _) in enumerate(tabs)
    )
    panels = "".join(
        '<div class="tab-panel{0}" id="tab-{1}">{2}</div>'.format(" active" if i == 0 else "", i, content)
        for i, (_, content) in enumerate(tabs)
    )

    doc = _TEMPLATE.replace("__NAV__", nav).replace("__PANELS__", panels)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "dashboard.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)

    if open_browser:
        webbrowser.open(os.path.abspath(path))

    print("Dashboard saved to {0}".format(path))
    return path
