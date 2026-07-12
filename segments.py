from collections import defaultdict

from cache import iter_cached_activities


def get_popular_segments(top_n=20):
    counts = defaultdict(lambda: {"name": None, "distance": None, "count": 0})

    for activity in iter_cached_activities():
        for effort in activity.get("segment_efforts", []):
            entry = counts[effort["id"]]
            entry["name"] = effort["name"]
            entry["distance"] = effort["distance"]
            entry["count"] += 1

    ranked = sorted(counts.items(), key=lambda kv: kv[1]["count"], reverse=True)
    return ranked[:top_n]


def print_popular_segments(top_n=20):
    ranked = get_popular_segments(top_n)
    if not ranked:
        print("\nNo segment data in cache yet. Run with --refresh to fetch segment efforts for cached activities.")
        return

    print("\nTop {0} most popular segments:".format(len(ranked)))
    for rank, (segment_id, info) in enumerate(ranked, start=1):
        distance_km = (info["distance"] or 0) / 1000
        print("{0:2d}. {1} - {2}x - {3:.1f} km - https://www.strava.com/segments/{4}".format(
            rank, info["name"], info["count"], distance_km, segment_id))
