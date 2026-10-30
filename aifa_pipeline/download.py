import hashlib
from pathlib import Path
import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .catalog import validate_url

MAX_BYTES = 30 * 1024 * 1024


def make_session():
    session = requests.Session()
    session.headers["User-Agent"] = "SQL-AIFA-academic-project/1.0"
    session.headers["Accept-Encoding"] = "identity"
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",), respect_retry_after_header=False)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_pdf(url: str, cache: Path, session, refresh=False, max_bytes=MAX_BYTES) -> bytes:
    if not validate_url(url):
        raise ValueError("Missing document URL")
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    pdf_path, manifest = cache / f"{key}.pdf", cache / f"{key}.json"
    if not refresh and pdf_path.exists() and manifest.exists():
        data = pdf_path.read_bytes()
        expected = json.loads(manifest.read_text())["sha256"]
        if hashlib.sha256(data).hexdigest() != expected or not data.startswith(b"%PDF-"):
            raise ValueError("Cached PDF checksum mismatch; rerun with --refresh")
        if len(data) > max_bytes:
            raise ValueError("Cached PDF exceeds the size limit")
        return data
    with session.get(url, timeout=(5, 20), stream=True, allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError(f"Expected HTTP 200, received {response.status_code}")
        chunks, size = [], 0
        for chunk in response.iter_content(chunk_size=65536):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("Downloaded PDF exceeds the size limit")
            chunks.append(chunk)
        data = b"".join(chunks)
    if not data.startswith(b"%PDF-"):
        raise ValueError("The server returned a non-PDF response")
    temporary = pdf_path.with_suffix(".part")
    temporary.write_bytes(data)
    temporary.replace(pdf_path)
    manifest.write_text(json.dumps({"url": url, "sha256": hashlib.sha256(data).hexdigest()}, indent=2) + "\n")
    return data
