import time
import json
from typing import Iterable
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "pointless-revision/0.1 (https://github.com/frankaugr/pointless; personal study tool)"


def run_sparql(query: str, retries: int = 3, backoff: float = 2.0) -> list[dict]:
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            url = f"{SPARQL_ENDPOINT}?{urlencode({'query': query})}"
            request = Request(url, headers=headers)
            with urlopen(request, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return _flatten_bindings(data["results"]["bindings"])
        except (URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff * (2 ** attempt))
    raise RuntimeError(f"Wikidata SPARQL failed after {retries} attempts: {last_exc}")


def _flatten_bindings(bindings: Iterable[dict]) -> list[dict]:
    out: list[dict] = []
    for row in bindings:
        flat: dict = {}
        for key, cell in row.items():
            flat[key] = cell.get("value")
        out.append(flat)
    return out


def qid_from_uri(uri: str) -> str | None:
    if not uri:
        return None
    return uri.rsplit("/", 1)[-1]
