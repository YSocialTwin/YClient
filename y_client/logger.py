import functools
import json
import os
import threading
import time
from datetime import datetime


_WRITE_LOCK = threading.Lock()


def _safe_int(value):
    try:
        return int(value)
    except Exception:
        return None


def _resolve_time_context(agent):
    sim_clock = getattr(agent, "sim_clock", None)
    day = _safe_int(getattr(sim_clock, "day", None))
    hour = _safe_int(getattr(sim_clock, "slot", None))
    return day, hour


def _client_log_path():
    return str(os.environ.get("YCLIENT_LOG_FILE", "") or "").strip()


def _append_log(payload):
    path = _client_log_path()
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        return
    try:
        line = json.dumps(payload, ensure_ascii=True)
    except Exception:
        return
    with _WRITE_LOCK:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def log_execution_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        error = None
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            error = exc
            raise
        finally:
            agent = args[0] if args else None
            day, hour = _resolve_time_context(agent)
            payload = {
                "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "method_name": func.__name__,
                "execution_time_seconds": round(
                    max(0.0, time.perf_counter() - started), 6
                ),
                "day": day,
                "hour": hour,
                "agent_name": getattr(agent, "name", None),
                "user_id": _safe_int(getattr(agent, "user_id", None)),
                "success": error is None,
            }
            if error is not None:
                payload["error"] = str(error)[:200]
            _append_log(payload)

    return wrapper
