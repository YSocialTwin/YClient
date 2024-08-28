import json


def generate_feed_data(keywords, suffix="", m=4):
    """
    Generate a fake feed data
    :param keywords: list of keywords to generate feeds for
    :param suffix: suffix to add to the research terms to specify a general context (e.g., 'Olympics')
    :param m: number of pages to search
    :return: list of feeds
    """

    feeds = []
    for k in keywords:
        k = k.replace(" ", "+")
        for i in range(1, m):
            rss_url = f"https://www.bing.com/news/search?format=RSS&q={k}+{suffix}&&first={i*11}"

            feed = {
                "url_site": "",
                "category": "",
                "leaning": "",
                "name": f"Bing - {k}",
                "feed_url": rss_url,
            }

            feeds.append(feed)
    return feeds


def generate_feed(filename, topics, suffix=""):
    """
    Generate topical rss feed using Bing search engine

    :param filename: the file to save the feeds
    :param topics: list of topics to generate feeds for
    :param suffix: suffix to add to the research terms to specify a general context (e.g., 'Olympics')
    """
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
        default="config_files/rss_feeds.json",
        help="JSON to save the generated feeds",
    )

    args = parser.parse_args()

    topics = args.topics.replace("_", " ").split(",")
    suffix = args.suffix
    out_file = args.out_file

    generate_feed(out_file, topics=topics, suffix=suffix)

