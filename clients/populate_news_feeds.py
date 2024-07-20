from y_client.utils import *
import json


def generate_feed_data(filename, topics, suffix=""):
    feeds = generate_feed_data(topics, suffix=suffix)
    json.dump(feeds, open(filename, "w"), indent=4)


if __name__ == "__main__":

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "-t",
        "--topics",
        help="list of topics to generate feeds for separated by commas",
    )
    parser.add_argument(
        "-s",
        "--suffix",
        default="",
        help="suffix to add to the research terms to specify a general context (e.g., 'Olympics')",
    )
    parser.add_argument(
        "-o",
        "--out_file",
        default="../config_files/rss_feeds.json",
        help="JSON to save the generated feeds",
    )

    args = parser.parse_args()

    topics = args.topics.split(",")
    suffix = args.suffix
    out_file = args.out_file

    generate_feed_data(out_file, topics, suffix=suffix)
