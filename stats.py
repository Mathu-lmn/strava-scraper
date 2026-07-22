from collections import defaultdict
from datetime import datetime

from cache import iter_cached_activities


def get_yearly_summary():
    """Aggregate cached activities by year: totals and a breakdown by activity type."""
    years = defaultdict(lambda: {
        "distance_km": 0.0, "moving_time_hours": 0.0, "count": 0, "by_type": defaultdict(lambda: {
            "distance_km": 0.0, "count": 0,
        }),
    })

    for activity in iter_cached_activities():
        start_date = activity.get("start_date")
        if not start_date:
            continue

        year = datetime.fromisoformat(start_date).year
        distance_km = (activity.get("distance") or 0) / 1000
        moving_hours = (activity.get("moving_time") or 0) / 3600
        activity_type = activity.get("type") or "Unknown"

        entry = years[year]
        entry["distance_km"] += distance_km
        entry["moving_time_hours"] += moving_hours
        entry["count"] += 1

        type_entry = entry["by_type"][activity_type]
        type_entry["distance_km"] += distance_km
        type_entry["count"] += 1

    return {
        year: {
            "distance_km": data["distance_km"],
            "moving_time_hours": data["moving_time_hours"],
            "count": data["count"],
            "by_type": dict(data["by_type"]),
        }
        for year, data in sorted(years.items())
    }


def print_yearly_summary():
    summary = get_yearly_summary()
    if not summary:
        print("\nNo cached activities to summarize yet.")
        return

    print("\nYearly summary:")
    for year, data in sorted(summary.items(), reverse=True):
        print("- {0}: {1:.1f} km, {2:.1f} h, {3} activities".format(
            year, data["distance_km"], data["moving_time_hours"], data["count"]))
        for activity_type, type_data in sorted(data["by_type"].items(), key=lambda kv: kv[1]["distance_km"], reverse=True):
            print("    {0}: {1:.1f} km ({2}x)".format(activity_type, type_data["distance_km"], type_data["count"]))
