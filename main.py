import argparse
import sys

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

import cache
import maps
import segments
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
    parser.add_argument("--all", action="store_true", help="Run every feature")
    return parser.parse_args()


def main():
    args = parse_args()

    ran_specific = any([
        args.full_map, args.weighted_map, args.heatmap,
        args.segments is not None, args.training_blocks,
    ])
    if args.all or not ran_specific:
        args.full_map = True
        args.weighted_map = True
        args.heatmap = True
        args.training_blocks = True
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

    if args.full_map:
        maps.build_full_map(open_browser=open_browser)

    if args.weighted_map:
        maps.build_weighted_map(open_browser=open_browser, progress=tqdm)

    if args.heatmap:
        maps.build_heatmap(open_browser=open_browser)

    if args.segments is not None:
        segments.print_popular_segments(top_n=args.segments)

    if args.training_blocks:
        training.print_training_blocks(activities)


if __name__ == "__main__":
    main()
