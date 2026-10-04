"""Shared helpers for the climate-modes pipeline: logging, HTTP, OPeNDAP ascii, dates."""
from __future__ import annotations

import datetime as dt
import email.utils
import os
import re
import sys
import threading
import time
from pathlib import Path

import numpy as np
import requests

_tls = threading.local()

BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/130.0 Safari/537.36'
    ),
    'Accept': '*/*',
}


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def log(*args):
    print(f'[{utcnow():%H:%M:%S}]', *args, file=sys.stderr, flush=True)


def session() -> requests.Session:
    if not hasattr(_tls, 's'):
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=4, max_retries=3)
        s.mount('https://', adapter)
        _tls.s = s
    return _tls.s


def http_get(url: str, headers: dict | None = None, timeout: int = 120, tries: int = 4) -> requests.Response:
    last = None
    for attempt in range(tries):
        try:
            r = session().get(url, headers=headers or BROWSER_HEADERS, timeout=timeout)
            if r.status_code in (200, 206):
                return r
            if r.status_code == 404:
                r.raise_for_status()
            last = requests.HTTPError(f'{r.status_code} for {url}')
        except requests.HTTPError:
            raise
        except requests.RequestException as e:  # network hiccup, retry
            last = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'GET failed: {url}: {last}')


def download(url: str, dest: Path, max_age_hours: float | None = None) -> Path:
    """Download `url` to `dest` unless a fresh enough copy exists (or the server's copy
    is not newer than ours)."""
    if dest.exists():
        if max_age_hours is None or time.time() - dest.stat().st_mtime < max_age_hours * 3600:
            return dest
        try:
            head = session().head(url, headers=BROWSER_HEADERS, timeout=60, allow_redirects=True)
            remote = email.utils.parsedate_to_datetime(head.headers['Last-Modified']).timestamp()
            if remote <= dest.stat().st_mtime:
                os.utime(dest)  # still current; check again after max_age_hours
                return dest
        except Exception:  # no Last-Modified: just download again
            pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f'download {url}')
    tmp = dest.with_suffix(dest.suffix + '.part')
    with session().get(url, headers=BROWSER_HEADERS, timeout=600, stream=True) as r:
        r.raise_for_status()
        with open(tmp, 'wb') as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(dest)
    return dest


def opendap_ascii(url: str, constraint: str) -> np.ndarray:
    """Fetch `var[a:s:b][..]` through the OPeNDAP .ascii service and return the array."""
    text = http_get(f'{url}.ascii?{constraint}', timeout=300).text
    body = text.split('-' * 45, 1)[1]
    m = re.search(r'^\s*([\w.]+)((?:\[\d+\])+)\s*$', body, re.M)
    if not m:
        raise ValueError(f'Unexpected OPeNDAP response for {constraint}: {text[:300]}')
    shape = [int(n) for n in re.findall(r'\[(\d+)\]', m.group(2))]
    values: list[float] = []
    for line in body[m.end():].splitlines():
        line = line.strip()
        if not line:
            if values:
                break
            continue
        if line.startswith('['):
            line = line.split(',', 1)[1] if ',' in line else ''
        elif len(shape) > 1:
            break
        values.extend(float(v) for v in line.split(',') if v.strip())
    arr = np.array(values, dtype=np.float64)
    arr[np.abs(arr) > 1e20] = np.nan  # _FillValue / missing_value
    return arr.reshape(shape)


def opendap_size(url: str, dim: str) -> int:
    dds = http_get(f'{url}.dds').text
    return int(re.search(rf'{dim} = (\d+)', dds).group(1))


def month_add(ym: tuple[int, int], k: int) -> tuple[int, int]:
    n = ym[0] * 12 + ym[1] - 1 + k
    return n // 12, n % 12 + 1


def ym_str(ym: tuple[int, int]) -> str:
    return f'{ym[0]:04d}-{ym[1]:02d}'


def rnd(x, nd: int = 2):
    """Round for JSON output; NaN becomes null."""
    x = float(x)
    return None if not np.isfinite(x) else round(x, nd)
