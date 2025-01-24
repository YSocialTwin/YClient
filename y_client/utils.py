import random
import json
import faker
try:
    from y_client import Agent, PageAgent
except:
    from y_client.classes.base_agent import Agent
    from y_client.classes.page_agent import PageAgent


def generate_user(config, owner=None):
    """
    Generate a fake user
    :param config: configuration dictionary
    :param owner: owner of the user
    :return: Agent object
    """

    locales = json.load(open("config_files/nationality_locale.json"))
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

    toxicity = fake.random_element(elements=(config["agents"]["toxicity_levels"]))

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
            min=config["agents"]["round_actions"]["min"],
            max=config["agents"]["round_actions"]["max"],
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
        toxicity=toxicity,
        api_key=api_key,
        is_page=0,
    )

    if not hasattr(agent, "user_id"):
        print("here")
        return None

    return agent


def generate_page(config, owner=None, name=None, feed_url=None):
    """
    Generate a fake page
    :param config: configuration dictionary
    :param name: name of the page
    :param feed_url: feed url of the page
    :return: Agent object
    """

    fake = faker.Faker()

    try:
        round_actions = fake.random_int(
            min=config["agents"]["round_actions"]["min"],
            max=config["agents"]["round_actions"]["max"],
        )
    except:
        round_actions = 3

    big_five = {
        "oe": fake.random_element(elements=(config["agents"]["big_five"]["oe"])),
        "co": fake.random_element(elements=(config["agents"]["big_five"]["co"])),
        "ex": fake.random_element(elements=(config["agents"]["big_five"]["ex"])),
        "ag": fake.random_element(elements=(config["agents"]["big_five"]["ag"])),
        "ne": fake.random_element(elements=(config["agents"]["big_five"]["ne"])),
    }

    api_key = config["servers"]["llm_api_key"]

    email = f"{name.replace(' ', '.')}@{fake.free_email_domain()}"

    page = PageAgent(
        name=name,
        pwd="",
        email=email,
        age=0,
        ag_type=fake.random_element(elements=(config["agents"]["llm_agents"])),
        leaning=None,
        interests=[],
        config=config,
        big_five=big_five,
        language=None,
        education_level=None,
        owner=owner,
        round_actions=round_actions,
        gender=None,
        nationality=None,
        toxicity=None,
        api_key=api_key,
        feed_url=feed_url,
        is_page=1,
    )

    return page
