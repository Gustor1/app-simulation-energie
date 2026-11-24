"""Appels HTTP avec timeout, nouvelles tentatives et cache local sur disque.

Le cache (fichiers JSON dans ``data/cache/`` par défaut) évite de dépendre du
réseau à chaque exécution : une requête déjà faite n'est pas refaite.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests

DEFAULT_CACHE_DIR = Path(os.environ.get("SIMU_CACHE_DIR", "data/cache"))
USER_AGENT = "simu-energie/0.1 (simulateur open source)"


def _session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    try:  # certificats du système (utile derrière un proxy d'entreprise qui inspecte le TLS)
        import ssl

        import truststore
        from requests.adapters import HTTPAdapter

        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        class _TrustStoreAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                kwargs["ssl_context"] = ctx
                return super().init_poolmanager(*args, **kwargs)

        session.mount("https://", _TrustStoreAdapter())
    except ImportError:
        pass
    return session


MIN_INTERVAL_S = 1.0  # délai minimal entre deux appels réseau (politesse envers les API)
_last_call = [0.0]


def _throttle() -> None:
    wait = _last_call[0] + MIN_INTERVAL_S - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.monotonic()


def cache_path(url: str, params: dict, cache_dir: Path) -> Path:
    key = json.dumps({"url": url, "params": params}, sort_keys=True)
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    name = url.rstrip("/").split("/")[-1] or "root"
    return Path(cache_dir) / f"{name}_{digest}.json"


def get_json(
    url: str,
    params: dict | None = None,
    *,
    cache_dir: Path | str | None = DEFAULT_CACHE_DIR,
    timeout: float = 60,
    retries: int = 5,
    backoff_s: float = 5,
):
    """GET JSON. Lit le cache s'il existe ; sinon interroge l'API et écrit le cache.

    ``cache_dir=None`` désactive le cache.
    """
    params = dict(params or {})
    path = cache_path(url, params, Path(cache_dir)) if cache_dir is not None else None
    if path is not None and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    session = _session()
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        _throttle()
        wait = backoff_s * attempt
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code == 429:  # limite de débit : on respecte Retry-After
                retry_after = response.headers.get("Retry-After", "")
                wait = float(retry_after) if retry_after.isdigit() else max(wait, 30 * attempt * (backoff_s > 0))
            response.raise_for_status()
            data = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(wait)
    else:
        raise ConnectionError(f"échec après {retries} tentatives : {url} {params}") from last_error

    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    return data
