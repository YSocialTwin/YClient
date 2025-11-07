"""
Utilities Module

This module provides utility functions for generating synthetic users and pages
for the Y social network simulation. It uses the Faker library to create realistic
user profiles with various demographic and personality attributes.

Functions:
    - generate_user: Generate a synthetic user agent with random attributes
    - generate_page: Generate a synthetic page agent for news feeds
"""

import json
import os
import random
from pathlib import Path

import faker

try:
    from y_client import Agent, PageAgent
except:
    from y_client.classes.base_agent import Agent
    from y_client.classes.page_agent import PageAgent


def generate_user(config, owner=None):
    """
    Generate a synthetic user agent with randomized attributes.
    
    This function creates a realistic user profile using the Faker library,
    with attributes drawn from the provided configuration. The generated user
    includes demographic information, personality traits, interests, and LLM settings.
    
    Args:
        config (dict): Configuration dictionary containing agent generation parameters.
                      Required keys include:
                      - agents.nationalities: List of nationalities to sample from
                      - agents.political_leanings: List of political leanings
                      - agents.age: Dict with min and max age values
                      - agents.interests: List of possible interests
                      - agents.n_interests: Dict with min and max number of interests
                      - agents.toxicity_levels: List of toxicity levels
                      - agents.languages: List of languages
                      - agents.llm_agents: List of LLM agent types
                      - agents.big_five: Big Five personality trait options
                      - agents.education_levels: List of education levels
                      - agents.round_actions: Dict with min and max daily actions
                      - servers.llm_api_key: API key for LLM services
        owner (str, optional): Username of the owner/creator of this agent. Defaults to None.
    
    Returns:
        Agent: A configured Agent object with randomized attributes, or None if creation fails.
               The agent includes: name, email, password, age, gender, nationality, 
               political leaning, interests, Big Five personality traits, education level,
               language, toxicity level, and LLM configuration.
    """

    BASE = Path(__file__).parent.absolute()
    BASE = str(BASE).split("y_client")[0]
    BASE = Path(BASE)

    locales = json.load(open(BASE / "config_files" / "nationality_locale.json"))
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
    Generate a synthetic page agent for publishing news content.
    
    This function creates a PageAgent that represents a news source or media outlet
    in the social network simulation. Unlike regular users, pages are designed to
    post news content from RSS feeds.
    
    Args:
        config (dict): Configuration dictionary containing agent generation parameters.
                      Required keys include:
                      - agents.round_actions: Dict with min and max daily actions
                      - agents.big_five: Big Five personality trait options
                      - agents.llm_agents: List of LLM agent types
                      - servers.llm_api_key: API key for LLM services
        owner (str, optional): Username of the owner/creator of this page. Defaults to None.
        name (str, optional): Name of the page/news source. Defaults to None.
        feed_url (str, optional): RSS feed URL for the page to pull news from. Defaults to None.
    
    Returns:
        PageAgent: A configured PageAgent object that can publish news content.
                  The page has minimal demographic attributes (no age, gender, nationality, etc.)
                  but includes LLM configuration and Big Five personality traits.
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
