import time
from threading import Lock

from fastapi import HTTPException

from app.core.config import get_settings


class LoginLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        settings = get_settings()
        now = time.monotonic()
        window = settings.login_window_seconds
        with self._lock:
            recent = [stamp for stamp in self._attempts.get(key, []) if now - stamp < window]
            self._attempts[key] = recent
            if len(recent) >= settings.login_attempt_limit:
                raise HTTPException(status_code=429, detail="Too many login attempts. Try again shortly.")

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._attempts.setdefault(key, []).append(time.monotonic())

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


login_limiter = LoginLimiter()
