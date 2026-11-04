"""YClientWeb (the client YWeb runs for the microblogging) installs the federation (World Simulation 1: 0 cross-posts).

`YClientWeb.__init__` never called `federation.install(config)`: `_state["enabled"]` stayed False, `post_fields()` returned {}
and the agents never asked the server for a destination, whatever `crosspost_propensity` and `crosspost_mode` said."""

import json
from types import SimpleNamespace

import pytest

from y_client import federation


def _config(tmp_path, fed=None):
    cfg = {
        "servers": {"api": "http://srv/"},
        "simulation": {
            "name": "wsim", "days": 1, "slots": 24, "population": "pop", "hourly_activity": {str(h): 0.1 for h in range(24)},
            "percentage_removed_agents_iteration": 0, "actions_likelihood": {"post": 1.0, "comment": 1.0},
            "agent_archetypes": {"enabled": False},
        },
        "agents": {"reading_from_follower_ratio": 0.5, "max_length_thread_reading": 5, "llm_agents": []},
        "posts": {"visibility_rounds": 36},
    }
    if fed is not None:
        cfg["federation"] = fed
    (tmp_path / "prompts.json").write_text(json.dumps({}))
    return cfg


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    import y_client.classes as classes
    from y_client.clients.client_web import YClientWeb

    monkeypatch.setattr(classes, "SimulationSlot", lambda config, *a, **k: SimpleNamespace(), raising=False)
    monkeypatch.delenv("CONTENT_DATABASE_URL", raising=False)

    def make(fed=None):
        return YClientWeb(_config(tmp_path, fed), str(tmp_path) + "/", first_run=True)

    yield make
    federation.install({})


def test_yclientweb_installs_the_federation_and_posts_cross_post_fields(make_client, monkeypatch):
    client = make_client({"enabled": True, "crosspost_mode": "agent_action", "crosspost_propensity": 1.0, "seed": 1})
    assert federation.enabled() and federation.agent_action()
    monkeypatch.setattr(federation.requests, "get",
                        lambda url, params=None, timeout=0: SimpleNamespace(json=lambda: {"destinations": ["forum"]}))
    fields = federation.post_fields(7, "a new post")
    assert fields["crosspost"] is True and [t["member"] for t in fields["crosspost_to"]] == ["forum"]
    assert client.actions_likelihood  # the rest of the constructor ran


def test_yclientweb_without_federation_stays_off(make_client):
    federation.install({"federation": {"enabled": True}})  # a previous state of the process is reset by the client
    make_client(None)
    assert not federation.enabled() and federation.post_fields(7, "a new post") == {}


def test_yclientweb_has_the_adoption_hook(make_client):
    client = make_client({"enabled": True, "adopt": True})
    assert callable(getattr(client, "adopt_federated_account", None))


def test_yclientweb_adopts_the_provisioned_accounts_as_agents_of_the_experiment(make_client, monkeypatch):
    """`federation.adopt_provisioned(client)` needs `client.adopt_federated_account`: YClientWeb had none."""
    import y_client.classes as classes

    class _Built:
        def __init__(self, **kw):
            self.kind, self.name, self.user_id, self.kw, self.activity_profile = type(self).__name__, kw["name"], 9, kw, None

        def set_prompts(self, prompts):
            pass

    class Real(_Built):
        pass

    class Fake(_Built):
        pass

    monkeypatch.setattr(classes, "Agent", Real, raising=False)
    monkeypatch.setattr(classes, "FakeAgent", Fake, raising=False)
    client = make_client({"enabled": True, "adopt": True})
    posted = []
    monkeypatch.setattr(federation.requests, "get", lambda url, timeout=0: SimpleNamespace(
        json=lambda: {"accounts": [{"user_id": 9, "username": "newcomer", "interests": ["jazz"]}]}))
    monkeypatch.setattr(federation.requests, "post", lambda url, json=None, timeout=0: posted.append((url, json)))
    assert federation.adopt_provisioned(client) == 1
    agent = client.agents.agents[0]
    assert (agent.kind, agent.name, agent.activity_profile, agent.simulation_client) == ("Real", "newcomer", "Always On", client)
    assert agent.kw["load"] is True and agent.kw["interests"] == ["jazz"] and agent.kw["recsys"] is not None
    # the server stores "default" for these accounts: the agent is saved with the recommenders it really uses
    assert (agent.content_rec_sys_name, agent.follow_rec_sys_name) == ("ReverseChronoPopularity", "Jaccard")
    assert posted == [("http://srv/federation/provisioned/adopted", {"user_ids": [9]})]
    assert client.adopt_federated_account({"user_id": 9, "username": "newcomer"}) is agent  # offered again: not duplicated
    assert len(client.agents.agents) == 1
    client.config["agents"]["llm_agents"] = [None]  # rule-based experiment: no model
    assert client.adopt_federated_account({"user_id": 10, "username": "other"}).kind == "Fake"


def test_a_saved_federation_agent_with_the_default_recommender_name_is_read_back(make_client, monkeypatch, tmp_path):
    """The population file kept "default" for an adopted account and `read_agents` raised AttributeError on resume,
    so the microblogging client of a World Simulation could not restart."""
    import y_client.classes as classes

    seen = []

    class Stub:
        def __init__(self, **kw):
            seen.append(kw)

        def set_prompts(self, prompts):
            pass

    monkeypatch.setattr(classes, "Agent", Stub, raising=False)
    monkeypatch.setattr(classes, "FakeAgent", Stub, raising=False)
    client = make_client(None)
    keys = ("oe", "co", "ex", "ag", "ne", "education_level", "nationality", "gender")
    entry = {"name": "JohnFord", "email": "j@federation.local", "password": "p", "type": "user", "leaning": "neutral",
             "interests": [[], []], "round_actions": 3, "toxicity": "no", "age": 0, "language": "en", "owner": "federation",
             "is_page": 0, "rec_sys": "default", "frec_sys": "default", **{k: None for k in keys}}
    (tmp_path / "pop.json").write_text(json.dumps({"agents": [entry]}))
    client.base_path = str(tmp_path)
    client.read_agents()
    assert [type(k["recsys"]).__name__ for k in seen] == ["ReverseChronoPopularity"]
    assert [type(k["frecsys"]).__name__ for k in seen] == ["Jaccard"]


def test_a_restart_lists_the_accounts_adopted_before(make_client, monkeypatch):
    """The population file holds only some of the accounts the server created: on a restart the client asks for all of them."""
    client = make_client({"enabled": True, "adopt": True})
    urls = []
    monkeypatch.setattr(federation.requests, "get", lambda url, timeout=0: urls.append(url) or SimpleNamespace(json=lambda: {"accounts": []}))
    federation.adopt_provisioned(client)
    federation.adopt_provisioned(client, include_adopted=True)
    assert urls[0].endswith("/federation/provisioned") and urls[1].endswith("/federation/provisioned?all=1")
