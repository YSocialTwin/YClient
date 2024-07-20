import faker
from y_client import Agent


def generate_user(config, owner=None):
    """
    Generate a fake user
    :return:
    """
    fake = faker.Faker()

    name = fake.name()
    email = f"{name.replace(' ', '.')}@{fake.free_email_domain()}"
    political_leaning = fake.random_element(
        elements=(config["agents"]["political_leanings"])
    )
    age = fake.random_int(
        min=config["agents"]["age"]["min"], max=config["agents"]["age"]["max"]
    )
    interests = fake.random_elements(
        elements=set(config["agents"]["interests"]),
        length=fake.random_int(
            min=config["agents"]["n_interests"]["min"],
            max=config["agents"]["n_interests"]["max"],
        ),
    )

    language = fake.random_element(elements=(config["agents"]["languages"]))

    ag_type = fake.random_element(elements=(config["agents"]["llm_agents"]))
    pwd = fake.password()

    big_five = {
        "oe": fake.random_element(elements=(config["agents"]["big_five"]["oe"])),
        "co": fake.random_element(elements=(config["agents"]["big_five"]["co"])),
        "ex": fake.random_element(elements=(config["agents"]["big_five"]["ex"])),
        "ag": fake.random_element(elements=(config["agents"]["big_five"]["ag"])),
        "ne": fake.random_element(elements=(config["agents"]["big_five"]["ne"])),
    }

    education_level = fake.random_element(
        elements=(config["agents"]["education_levels"])
    )

    api_key = config["servers"]["llm_api_key"]

    agent = Agent(
        name=name.replace(" ", ""),
        pwd=pwd,
        email=email,
        age=age,
        ag_type=ag_type,
        leaning=political_leaning,
        interests=list(interests),
        config=config,
        big_five=big_five,
        language=language,
        education_level=education_level,
        owner=owner,
        api_key=api_key,
    )

    return agent



def generate_feed_data(keywords, suffix="", m=4):
    """
    Generate a fake feed data
    :return:
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
