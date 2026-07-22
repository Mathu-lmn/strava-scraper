import argparse
import sys

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

import cache
import dashboard
import maps
import segments
import stats
import training
from login import login


def parse_args():
    parser = argparse.ArgumentParser(description="Strava activities scraper & map generator")
    parser.add_argument("--no-fetch", action="store_true", help="Don't sync activities from Strava, use the local cache as-is")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch and overwrite every cached activity")
    parser.add_argument("--no-browser", action="store_true", help="Don't open generated maps in a browser")
    parser.add_argument("--full-map", action="store_true", help="Generate the full (unweighted) activities map")
    parser.add_argument("--weighted-map", action="store_true", help="Generate the weighted activities map (heavy)")
    parser.add_argument("--heatmap", action="store_true", help="Generate a heatmap of all activities")
    parser.add_argument("--segments", type=int, nargs="?", const=20, default=None, metavar="N",
                         help="Print the N most popular segments (default 20)")
    parser.add_argument("--training-blocks", action="store_true", help="Detect training blocks leading up to races")
    parser.add_argument("--stats", action="store_true", help="Print a yearly mileage/time summary")
    parser.add_argument("--all", action="store_true", help="Run every feature")
    return parser.parse_args()


def main():
    args = parse_args()

    ran_specific = any([
        args.full_map, args.weighted_map, args.heatmap,
        args.segments is not None, args.training_blocks, args.stats,
    ])
    if args.all or not ran_specific:
        args.full_map = True
        args.weighted_map = True
        args.heatmap = True
        args.training_blocks = True
        args.stats = True
        if args.segments is None:
            args.segments = 20

    try:
        client = login()
    except Exception as e:
        print("Error: {0}".format(e))
        sys.exit(1)

    activities = []
    if not args.no_fetch:
        activities = cache.sync_activities(client, force_refresh=args.refresh, progress=tqdm)
    elif args.training_blocks:
        activities = list(client.get_activities())

    open_browser = not args.no_browser

    map_paths = {}
    if args.full_map:
        map_paths["Full Map"] = maps.build_full_map(open_browser=False)

    if args.weighted_map:
        map_paths["Weighted Map"] = maps.build_weighted_map(open_browser=False, progress=tqdm)

    if args.heatmap:
        map_paths["Heatmap"] = maps.build_heatmap(open_browser=False)

    segment_stats = None
    if args.segments is not None:
        segments.print_popular_segments(top_n=args.segments)
        segment_stats = segments.get_segment_stats(top_n=args.segments)

    training_blocks = None
    if args.training_blocks:
        training.print_training_blocks(activities)
        training_blocks = training.find_training_blocks(activities)

    yearly_summary = None
    if args.stats:
        stats.print_yearly_summary()
        yearly_summary = stats.get_yearly_summary()

    dashboard.build_dashboard(
        maps=map_paths,
        segment_stats=segment_stats,
        training_blocks=training_blocks,
        yearly_summary=yearly_summary,
        open_browser=open_browser,
    )


if __name__ == "__main__":
    main()
