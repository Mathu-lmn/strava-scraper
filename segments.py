from collections import defaultdict

from cache import iter_cached_activities


def _format_duration(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return "{0}:{1:02d}:{2:02d}".format(hours, minutes, secs)
    return "{0}:{1:02d}".format(minutes, secs)


def get_segment_stats(top_n=None):
    """Aggregate cached segment efforts by segment: attempt count and PR (fastest time)."""
    stats = defaultdict(lambda: {
        "name": None, "distance": None, "count": 0, "best_time": None, "best_date": None,
    })

    for activity in iter_cached_activities():
        activity_date = activity.get("start_date")
        for effort in activity.get("segment_efforts", []):
            entry = stats[effort["id"]]
            entry["name"] = effort["name"]
            entry["distance"] = effort["distance"]
            entry["count"] += 1

            elapsed = effort.get("elapsed_time")
            if elapsed is not None and (entry["best_time"] is None or elapsed < entry["best_time"]):
                entry["best_time"] = elapsed
                entry["best_date"] = activity_date

    ranked = sorted(stats.items(), key=lambda kv: kv[1]["count"], reverse=True)
    return ranked[:top_n] if top_n else ranked


def print_popular_segments(top_n=20):
    ranked = get_segment_stats(top_n)
    if not ranked:
        print("\nNo segment data in cache yet. Run with --refresh to fetch segment efforts for cached activities.")
        return

    print("\nTop {0} most popular segments:".format(len(ranked)))
    for rank, (segment_id, info) in enumerate(ranked, start=1):
        distance_km = (info["distance"] or 0) / 1000
        pr = ""
        if info["best_time"] is not None:
            date = info["best_date"][:10] if info["best_date"] else "?"
            pr = " - PR {0} on {1}".format(_format_duration(info["best_time"]), date)
        print("{0:2d}. {1} - {2}x - {3:.1f} km{4} - https://www.strava.com/segments/{5}".format(
            rank, info["name"], info["count"], distance_km, pr, segment_id))
