import random
import json
import faker
from y_client import Agent

def generate_user(config, owner=None):
    """
    Generate a fake user
    :param config: configuration dictionary
    :param owner: owner of the user
    :return: Agent object
    """

    locales = json.load(open("../config_files/nationality_locale.json"))
    try:
        nationality = random.sample(config["agents"]["nationalities"], 1)[0]
    except:
        nationality = "American"

    gender = random.sample(["male", "female"], 1)[0]

    fake = faker.Faker(locales[nationality])

    if gender == "male":
        name = fake.name_male()
    else:
        name = fake.name_female()

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

    try:
        round_actions = fake.random_int(
            min=config["agents"]["round_actions"]["min"], max=config["agents"]["round_actions"]["max"]
        )
    except:
        round_actions = 3

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
        round_actions=round_actions,
        gender=gender,
        nationality=nationality,
        api_key=api_key,
    )

    return agent



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
