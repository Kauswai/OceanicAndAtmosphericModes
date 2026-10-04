"""
Global relative atmospheric angular momentum (AAM) from GEFS zonal wind.

    M_r = (2 pi a^3 / g) * integral_p integral_phi [u] cos^2(phi) dphi dp

on the 12 GEFS pgrb2a pressure levels (1000-10 hPa). The anomaly is taken against the
NCEP/NCAR R1 1991-2020 monthly climatology computed on the same levels (smoothed to a
daily cycle), plus a fixed GEFS-minus-R1 offset fitted by calibrate_aam.py over the
period both were available (R1 stopped in March 2026).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests

from common import http_get, log, opendap_ascii, session, utcnow

A = 6.371e6
G = 9.80665
LEVELS = [1000, 925, 850, 700, 500, 400, 300, 250, 200, 100, 50, 10]  # hPa
SIGMA = 1.2e25  # std of daily relative AAM anomalies (Weickmann & Berry GSDM)
UNIT = 1e25

GEFS = 'https://noaa-gefs-pds.s3.amazonaws.com'
GEFS_MEMBERS = ['gec00'] + [f'gep{i:02d}' for i in range(1, 31)]
R1_LTM = 'https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis/Monthlies/pressure/uwnd.mon.ltm.1991-2020.nc'
R1_LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10]
CALIBRATION_PATH = Path(__file__).with_name('aam_calibration.json')


def aam_from_zonal_mean(ubar: np.ndarray, lats: np.ndarray, levels=LEVELS) -> float:
    """ubar: (nlev, nlat) zonal-mean u (m/s); lats in degrees; levels in hPa."""
    phi = np.deg2rad(lats)
    order = np.argsort(phi)
    lat_int = np.trapezoid(ubar[:, order] * np.cos(phi[order]) ** 2, phi[order], axis=1)  # (nlev,)
    p = np.array(levels, dtype=float) * 100.0
    o = np.argsort(p)
    return float(2 * np.pi * A**3 / G * np.trapezoid(lat_int[o], p[o]))


# --------------------------------------------------------------------------------------
# Climatology (R1 monthly LTM on the GEFS level set)
# --------------------------------------------------------------------------------------

def r1_monthly_climatology() -> np.ndarray:
    """(12,) R1 1991-2020 monthly relative AAM."""
    lev_idx = [R1_LEVELS.index(lv) for lv in LEVELS]
    lats = np.arange(90, -90.1, -2.5)
    out = []
    for m in range(12):
        u = opendap_ascii(R1_LTM, f'uwnd[{m}:1:{m}][0:1:16][0:1:72][0:1:143]')[0]  # (17, 73, 144)
        out.append(aam_from_zonal_mean(u[lev_idx].mean(axis=2), lats))
    return np.array(out)


def daily_climatology(monthly: np.ndarray, day: dt.date) -> float:
    """Mean + 2 harmonics through the 12 monthly values (placed mid-month)."""
    t = (np.arange(12) + 0.5) / 12 * 2 * np.pi
    cols = [np.ones(12)]
    for k in (1, 2):
        cols += [np.cos(k * t), np.sin(k * t)]
    coef = np.linalg.lstsq(np.array(cols).T, monthly, rcond=None)[0]
    x = (day.timetuple().tm_yday - 0.5) / 365.25 * 2 * np.pi
    feats = [1.0]
    for k in (1, 2):
        feats += [np.cos(k * x), np.sin(k * x)]
    return float(np.dot(coef, feats))


# --------------------------------------------------------------------------------------
# GEFS reading
# --------------------------------------------------------------------------------------

_grib_lock = threading.Lock()


def decode_grib(buf: bytes) -> np.ndarray:
    import eccodes

    with _grib_lock:
        gid = eccodes.codes_new_from_message(buf)
        try:
            ni = eccodes.codes_get(gid, 'Ni')
            nj = eccodes.codes_get(gid, 'Nj')
            vals = eccodes.codes_get_values(gid).reshape(nj, ni)
            if eccodes.codes_get(gid, 'jScansPositively'):
                vals = vals[::-1]
        finally:
            eccodes.codes_release(gid)
    return vals


def gefs_url(init: dt.datetime, member: str, fhour: int) -> str:
    d = init.strftime('%Y%m%d')
    h = init.strftime('%H')
    return f'{GEFS}/gefs.{d}/{h}/atmos/pgrb2ap5/{member}.t{h}z.pgrb2a.0p50.f{fhour:03d}'


def gefs_exists(init: dt.datetime, member: str, fhour: int) -> bool:
    try:
        return session().head(gefs_url(init, member, fhour) + '.idx', timeout=30).status_code == 200
    except requests.RequestException:
        return False


class AamReader:
    """Relative AAM of one GEFS file, cached as a single number per file."""

    def __init__(self, cache_dir: Path | None):
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache(self, init: dt.datetime, member: str, fhour: int) -> Path | None:
        return self.cache_dir / f'{init:%Y%m%d%H}_{member}_f{fhour:03d}.json' if self.cache_dir else None

    def aam(self, init: dt.datetime, member: str, fhour: int) -> float:
        cf = self._cache(init, member, fhour)
        if cf and cf.exists():
            return json.loads(cf.read_text())['aam']
        url = gefs_url(init, member, fhour)
        idx = http_get(url + '.idx').text.splitlines()
        offsets = [int(line.split(':')[1]) for line in idx]
        ubar = []
        for lev in LEVELS:
            key = f':UGRD:{lev} mb:'
            pos = next(i for i, line in enumerate(idx) if key in line)
            end = offsets[pos + 1] - 1 if pos + 1 < len(offsets) else ''
            for _ in range(4):
                buf = http_get(url, headers={'Range': f'bytes={offsets[pos]}-{end}'}).content
                if buf[:4] == b'GRIB' and buf[-4:] == b'7777':
                    break
                time.sleep(2)
            else:
                raise RuntimeError(f'Incomplete GRIB message {url} {key}')
            ubar.append(decode_grib(buf).mean(axis=1))  # (361,) zonal mean, 90N -> 90S
        value = aam_from_zonal_mean(np.array(ubar), np.linspace(90, -90, 361))
        if cf:
            tmp = cf.with_suffix('.tmp')
            tmp.write_text(json.dumps({'aam': value}))
            os.replace(tmp, cf)
        return value

    def prune(self, keep_days: int = 200):
        if not self.cache_dir:
            return
        cutoff = utcnow() - dt.timedelta(days=keep_days)
        for f in self.cache_dir.glob('*.json'):
            try:
                if dt.datetime.strptime(f.name[:10], '%Y%m%d%H') < cutoff:
                    f.unlink()
            except ValueError:
                pass


def latest_init(max_lead: int) -> dt.datetime:
    now = utcnow()
    day = dt.datetime(now.year, now.month, now.day)
    for back in range(4):
        init = day - dt.timedelta(days=back)
        if gefs_exists(init, GEFS_MEMBERS[-1], max_lead):
            return init
    raise RuntimeError('No complete GEFS 00Z run found in the last 4 days')


def load_calibration() -> dict:
    if CALIBRATION_PATH.exists():
        return json.loads(CALIBRATION_PATH.read_text())
    return {'offset': 0.0}


def build(cache: Path | None, pool: ThreadPoolExecutor, history_days: int = 120, lead_days: int = 16) -> dict:
    reader = AamReader(cache / 'aam' if cache else None)
    clim_monthly = r1_monthly_climatology()
    offset = load_calibration()['offset']

    init = latest_init(24 * lead_days)
    d0 = init.date()
    log(f'AAM: GEFS init {init:%Y-%m-%d %HZ}, {history_days} analysis days, {lead_days} lead days')

    def anomaly(day: dt.date, value: float) -> float:
        return (value - offset - daily_climatology(clim_monthly, day)) / UNIT

    hist_days = [d0 - dt.timedelta(days=k) for k in range(history_days, 0, -1)]
    hist_jobs = {
        d: pool.submit(reader.aam, dt.datetime(d.year, d.month, d.day), 'gec00', 0) for d in hist_days + [d0]
    }
    fc_days = [d0 + dt.timedelta(days=k) for k in range(lead_days + 1)]
    fc_jobs = {
        (m, k): pool.submit(reader.aam, init, m, 24 * k) for m in GEFS_MEMBERS for k in range(1, lead_days + 1)
    }

    hist = []
    for d in hist_days:
        try:
            hist.append((d, anomaly(d, hist_jobs[d].result())))
        except Exception as e:  # a missing analysis should not kill the run
            log(f'AAM analysis {d} failed: {e}')
    a0 = anomaly(d0, hist_jobs[d0].result())
    members = []
    for m in GEFS_MEMBERS:
        members.append([a0] + [anomaly(fc_days[k], fc_jobs[(m, k)].result()) for k in range(1, lead_days + 1)])
    reader.prune()
    members = np.array(members)
    return {
        'init': init.strftime('%Y-%m-%dT%H:%MZ'),
        'hist': hist + [(d0, a0)],
        'dates': [d.isoformat() for d in fc_days],
        'members': members,
        'sigma': SIGMA / UNIT,
    }
