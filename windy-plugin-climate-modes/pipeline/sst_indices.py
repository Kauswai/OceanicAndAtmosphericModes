"""
SST-based climate indices, computed the same way from observed (ERSSTv5) and forecast
(NMME / CFSv2) monthly SST anomalies on the ERSSTv5 2-degree grid.

Grid: lat 88 .. -88 (89 rows), lon 0 .. 358 (180 columns). Land points are NaN.

  nino34   5S-5N, 170W-120W                     ENSO
  nino3/4/12                                    other Nino regions (map only)
  dmi      10S-10N 50-70E  minus  10S-0 90-110E  Indian Ocean Dipole
  atl3     3S-3N, 20W-0                          Atlantic Nino / Atlantic equatorial mode
  amo      0-60N 80W-0  minus  60S-60N mean      AMO, Trenberth & Shea (2006) definition
  pdo      projection of North Pacific (20-70N) anomalies on a pattern regressed onto
           the NCEI ERSST PDO (calibrate.py)
  pmm      projection of 21S-32N, 175E-95W anomalies with the cold-tongue (CTI) signal
           removed, on a pattern regressed onto the Chiang & Vimont PMM SST index
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

LATS = np.arange(88.0, -88.1, -2.0)
LONS = np.arange(0.0, 360.0, 2.0)
LAT2D, LON2D = np.meshgrid(LATS, LONS, indexing='ij')
WEIGHTS = np.cos(np.deg2rad(LAT2D))

PATTERNS_PATH = Path(__file__).with_name('patterns.json')

# (south, north, west, east), longitudes in degrees east; west > east wraps through 0
REGIONS: dict[str, tuple[float, float, float, float]] = {
    'nino34': (-5, 5, 190, 240),
    'nino3': (-5, 5, 210, 270),
    'nino4': (-5, 5, 160, 210),
    'nino12': (-10, 0, 270, 280),
    'iod_w': (-10, 10, 50, 70),
    'iod_e': (-10, 0, 90, 110),
    'atl3': (-3, 3, 340, 360),
    'natl': (0, 60, 280, 360),
    'glob60': (-60, 60, 0, 360),
    'cti': (-6, 6, 180, 270),
    'pdo': (20, 70, 110, 260),
    'pmm': (-21, 32, 175, 265),
}


def box_mask(name: str) -> np.ndarray:
    s, n, w, e = REGIONS[name]
    lat_ok = (LAT2D >= s) & (LAT2D <= n)
    if e - w >= 360:
        lon_ok = np.ones_like(LAT2D, dtype=bool)
    else:
        lon = (LON2D - w) % 360
        lon_ok = lon <= (e - w) % 360 if (e - w) % 360 else lon == 0
    m = lat_ok & lon_ok
    if name == 'pmm':
        m &= ~((LAT2D >= 18) & (LON2D >= 262))  # Gulf of Mexico
    if name == 'natl':
        m &= ~((LAT2D <= 8) & (LON2D <= 282))  # Pacific side of Central America
    return m


MASKS = {k: box_mask(k) for k in REGIONS}


def box_mean(anom: np.ndarray, name: str) -> np.ndarray:
    """Area-weighted mean over a region; anom (..., 89, 180) with NaN for land."""
    m = MASKS[name]
    a = anom[..., m]
    w = np.broadcast_to(WEIGHTS[m], a.shape)
    ok = np.isfinite(a)
    return np.where(ok, a * w, 0).sum(-1) / np.maximum(np.where(ok, w, 0).sum(-1), 1e-9)


def load_patterns() -> dict:
    """Patterns fitted by calibrate.py (PDO, PMM, CTI regression)."""
    raw = json.loads(PATTERNS_PATH.read_text())
    out = {}
    for key in ('pdo', 'pmm'):
        p = raw[key]
        field = np.full(LAT2D.shape, np.nan)
        beta = np.full(LAT2D.shape, np.nan)
        for lat, lon, v, *rest in p['points']:
            i = int(round((88 - lat) / 2))
            j = int(round(lon / 2)) % 180
            field[i, j] = v
            if rest:
                beta[i, j] = rest[0]
        out[key] = {**p, 'field': field, 'beta': beta}
    return out


def project(anom: np.ndarray, pattern: dict) -> np.ndarray:
    """Area-weighted projection of anomaly fields onto a stored pattern, calibrated."""
    field = pattern['field']
    m = np.isfinite(field)
    a = anom[..., m]
    p = field[m]
    w = WEIGHTS[m]
    ok = np.isfinite(a)
    num = np.where(ok, a * p * w, 0).sum(-1)
    den = np.where(ok, p * p * w, 0).sum(-1)
    return pattern['a'] * num / np.maximum(den, 1e-12) + pattern['b']


def compute_indices(anom: np.ndarray, patterns: dict | None) -> dict[str, np.ndarray]:
    """All indices for anomaly fields with shape (..., 89, 180)."""
    out = {k: box_mean(anom, k) for k in ('nino34', 'nino3', 'nino4', 'nino12', 'atl3')}
    out['iod_w'] = box_mean(anom, 'iod_w')
    out['iod_e'] = box_mean(anom, 'iod_e')
    out['dmi'] = out['iod_w'] - out['iod_e']
    g = box_mean(anom, 'glob60')
    out['amo'] = box_mean(anom, 'natl') - g
    if patterns:
        out['pdo'] = project(anom, patterns['pdo'])
        cti = box_mean(anom, 'cti')
        resid = anom - patterns['pmm']['beta'] * cti[..., None, None]
        out['pmm'] = project(resid, patterns['pmm'])
    return out
