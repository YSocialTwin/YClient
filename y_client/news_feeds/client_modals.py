"""
Client Models Module

This module defines SQLAlchemy database models for storing news-related data
in the Y social network simulation. It manages the local database for articles,
websites, images, and custom agent prompts.

The module automatically initializes a SQLite database from a clean schema
template when starting a new simulation.

Database Models:
    - Articles: News articles fetched from RSS feeds
    - Websites: News sources/websites with RSS feeds
    - Images: Images associated with articles
    - Agent_Custom_Prompt: Custom LLM prompts for specific agents

Global Objects:
    - base: SQLAlchemy declarative base
    - engine: Database engine connection
    - session: Scoped session for database operations
"""

import json
import os
import os.path
import shutil
from pathlib import Path

import sqlalchemy as db
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base


base = declarative_base()
engine = None
session = None


class Articles(base):
    """
    Database model for news articles.
    
    Attributes:
        id (int): Primary key
        title (str): Article title (max 200 chars)
        summary (str): Article summary/description (max 800 chars)
        website_id (int): Foreign key to Websites table
        fetched_on (int): Date fetched in YYYYMMDD format
        link (str): URL to the full article (max 200 chars)
    """
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(800))
    website_id = db.Column(db.Integer, nullable=False)
    fetched_on = db.Column(db.Integer, nullable=False)
    link = db.Column(db.String(200), nullable=False)


class Websites(base):
    """
    Database model for news websites/sources.
    
    Attributes:
        id (int): Primary key
        name (str): Website/source name (max 100 chars)
        rss (str): RSS feed URL (max 200 chars)
        country (str): Country of origin (max 50 chars)
        language (str): Primary language (max 50 chars)
        leaning (str): Political leaning (max 50 chars)
        category (str): Content category (max 50 chars)
        last_fetched (int): Last fetch date in YYYYMMDD format
    """
    __tablename__ = "websites"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rss = db.Column(db.String(200), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    leaning = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    last_fetched = db.Column(db.Integer, nullable=False)


class Images(base):
    """
    Database model for images associated with articles.
    
    Attributes:
        id (int): Primary key
        url (str): Image URL (max 200 chars)
        description (str): Image description (max 400 chars)
        article_id (int): Foreign key to Articles table (local articles)
        remote_article_id (int): ID of article on remote server
    """
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=True)
    description = db.Column(db.String(400), nullable=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=True)
    remote_article_id = db.Column(db.Integer, nullable=True)


class Agent_Custom_Prompt(base):
    """
    Database model for custom LLM prompts per agent.
    
    Allows individual agents to have personalized system prompts
    for content generation.
    
    Attributes:
        id (int): Primary key
        agent_name (str): Name of the agent
        prompt (str): Custom prompt text
    """
    __tablename__ = "agent_custom_prompt"
    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.TEXT, nullable=False)
    prompt = db.Column(db.TEXT, nullable=False)


def _legacy_default_db_path():
    database_url = os.environ.get("CONTENT_DATABASE_URL")
    if database_url:
        return None, database_url

    try:
        config = json.load(open("experiments/current_config.json"))
        db_name = config["simulation"]["name"]
        return f"experiments/{db_name}.db", None
    except Exception:
        return None, None


def _ensure_sqlite_seed_db(target_path):
    if target_path is None or os.path.exists(target_path):
        return
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    shutil.copyfile(
        f"{base_dir}/../../data_schema/database_clean_client.db",
        target_path,
    )


def initialize_client_db(*, db_path=None, database_url=None):
    global engine, session

    if db_path is None and database_url is None:
        db_path, database_url = _legacy_default_db_path()

    if database_url:
        engine = db.create_engine(database_url)
    elif db_path:
        _ensure_sqlite_seed_db(db_path)
        engine = db.create_engine(f"sqlite:////{os.path.abspath(db_path)}")
    else:
        engine = None
        session = None
        return None, None, base

    base.metadata.bind = engine
    session = orm.scoped_session(orm.sessionmaker())(bind=engine)
    return session, engine, base


def get_session():
    return session


def get_engine():
    return engine


initialize_client_db()
