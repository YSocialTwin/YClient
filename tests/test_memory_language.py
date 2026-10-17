"""The memory package renders its texts in the language of the simulation prompts."""
from types import SimpleNamespace

import pytest

pytest.importorskip("yclient_memory")
from yclient_memory.config import MemoryConfig  # noqa: E402

if "language" not in MemoryConfig.__dataclass_fields__:  # yclient-memory < 0.2.0 runs in English
    pytest.skip("yclient-memory without language support", allow_module_level=True)

from y_client import memory_runtime, prompt_store  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_language():
    previous = prompt_store.current_language()
    yield
    prompt_store.set_language(previous or "en")


def _agent():
    return SimpleNamespace(memory_enabled=True, memory_backend="simple_recent", name="a", user_id=1)


@pytest.mark.parametrize("language", ["en", "it"])
def test_engine_uses_the_simulation_prompt_language(language):
    prompt_store.set_language(language)
    _, engine = memory_runtime.build_agent_memory_engine(_agent())
    assert engine.config.language == language


def test_english_is_the_default_language():
    prompt_store.set_language("en")
    _, engine = memory_runtime.build_agent_memory_engine(_agent())
    assert engine.config.language == "en"


def test_old_package_warns_once_and_keeps_running(caplog, monkeypatch):
    class OldConfig:  # no ``language`` field, like yclient-memory 0.1.x
        __dataclass_fields__ = {}

    monkeypatch.setattr(memory_runtime, "_LANGUAGE_WARNED", False)
    with caplog.at_level("WARNING"):
        memory_runtime._warn_if_language_unsupported(OldConfig, "it")
        memory_runtime._warn_if_language_unsupported(OldConfig, "it")
    assert len([r for r in caplog.records if "older than 0.2.0" in r.getMessage()]) == 1


def test_missing_package_message_names_the_plugin(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("yclient_memory"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="Agent Memory"):
        memory_runtime._load_memory_package()
