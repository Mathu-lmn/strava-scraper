import json
import os
import time

import requests
from stravalib.exc import Fault, RateLimitExceeded

CACHE_DIR = "cache"
MAX_RETRIES = 3


def _cache_path(activity_id):
    return os.path.join(CACHE_DIR, "activity-{0}.json".format(activity_id))


def _legacy_polyline(activity_id):
    legacy_path = os.path.join(CACHE_DIR, "map-{0}.json".format(activity_id))
    if os.path.exists(legacy_path):
        with open(legacy_path, "r") as f:
            poly = f.read().strip()
            return poly or None
    return None


def _type_str(activity_type):
    return activity_type.root if activity_type is not None else None


def read_cached_activity(activity_id):
    path = _cache_path(activity_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None


def write_cached_activity(activity_id, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(activity_id), "w") as f:
        json.dump(data, f)


def iter_cached_activities():
    if not os.path.isdir(CACHE_DIR):
        return
    for file in sorted(os.listdir(CACHE_DIR)):
        if file.startswith("activity-") and file.endswith(".json"):
            with open(os.path.join(CACHE_DIR, file), "r") as f:
                try:
                    yield json.load(f)
                except json.JSONDecodeError:
                    continue


def _fetch_detail(client, activity_id):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.get_activity(activity_id, include_all_efforts=True)
        except RateLimitExceeded as e:
            wait = (e.timeout or 60) + 1
            print("Strava rate limit reached, waiting {0}s...".format(wait))
            time.sleep(wait)
        except (Fault, requests.exceptions.RequestException) as e:
            if attempt == MAX_RETRIES:
                raise
            wait = 2 ** attempt
            print("Error fetching activity {0} ({1}), retrying in {2}s ({3}/{4})...".format(
                activity_id, e, wait, attempt, MAX_RETRIES))
            time.sleep(wait)
    raise RuntimeError("Could not fetch activity {0}".format(activity_id))


def sync_activities(client, force_refresh=False, progress=None):
    """Fetch the athlete's activities and populate the local cache.

    Returns the list of activities (as returned by the Strava API).
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    activities = list(client.get_activities())
    print("Found {0} activities on Strava".format(len(activities)))

    to_process = [
        a for a in activities if force_refresh or read_cached_activity(a.id) is None
    ]
    iterable = progress(to_process, desc="Fetching activities", unit="activity") if progress else to_process

    fetched, skipped = 0, 0
    for activity in iterable:
        try:
            detail = _fetch_detail(client, activity.id)
        except Exception as e:
            print("Skipping activity {0} after repeated failures: {1}".format(activity.id, e))
            skipped += 1
            continue

        poly = (detail.map.polyline or detail.map.summary_polyline) if detail.map else None
        if not poly:
            poly = _legacy_polyline(activity.id)
        if not poly:
            print("Activity {0} has no polyline data, skipping".format(activity.id))
            skipped += 1
            continue

        segment_efforts = [
            {
                "id": effort.segment.id,
                "name": effort.segment.name,
                "distance": float(effort.segment.distance) if effort.segment.distance is not None else None,
            }
            for effort in (detail.segment_efforts or [])
            if effort.segment is not None
        ]

        write_cached_activity(activity.id, {
            "id": activity.id,
            "name": detail.name,
            "type": _type_str(detail.type),
            "workout_type": detail.workout_type,
            "start_date": detail.start_date.isoformat() if detail.start_date else None,
            "distance": float(detail.distance) if detail.distance is not None else None,
            "moving_time": int(detail.moving_time) if detail.moving_time is not None else None,
            "polyline": poly,
            "segment_efforts": segment_efforts,
        })
        fetched += 1

    print("Cached {0} new activities ({1} skipped, {2} already up to date)".format(
        fetched, skipped, len(activities) - len(to_process)))

    return activities
