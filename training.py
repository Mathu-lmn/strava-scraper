from datetime import timedelta

# Strava workout_type: Run race = 1, Ride race = 11
RACE_WORKOUT_TYPES = {1, 11}
MAX_GAP = timedelta(days=7)


def find_training_blocks(activities):
    """Group activities into training blocks that lead up to a race, where
    a block is broken by any gap longer than one week between activities."""
    dated = sorted(
        (a for a in activities if a.start_date is not None),
        key=lambda a: a.start_date,
    )

    blocks = []
    used_until = -1

    for i, activity in enumerate(dated):
        if activity.workout_type not in RACE_WORKOUT_TYPES:
            continue

        start = i
        while start > used_until + 1:
            gap = dated[start].start_date - dated[start - 1].start_date
            if gap > MAX_GAP:
                break
            start -= 1

        blocks.append({"race": activity, "activities": dated[start:i + 1]})
        used_until = i

    return blocks


def print_training_blocks(activities):
    blocks = find_training_blocks(activities)
    if not blocks:
        print("\nNo races found (no activity with a 'Race' workout type).")
        return

    print("\nFound {0} training block(s):".format(len(blocks)))
    for block in blocks:
        race = block["race"]
        acts = block["activities"]
        total_distance_km = sum((a.distance or 0) for a in acts) / 1000
        span_days = (race.start_date - acts[0].start_date).days
        print("\n- Race: {0} ({1})".format(race.name, race.start_date.date()))
        print("  {0} activities over {1} days, {2:.1f} km total".format(len(acts), span_days, total_distance_km))
