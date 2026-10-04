#!/usr/bin/env python3
"""
Climate modes & oscillations pipeline for windy-plugin-climate-modes -> modes.json

Equatorial modes (shown on the map and in the panel)
  ENSO (Nino 3.4, plus Nino 1+2 / 3 / 4), IOD (DMI and its two poles), Atlantic Nino (ATL3)
    daily     NOAA OISST v2.1 anomalies (1991-2020), last ~150 days
    monthly   NOAA ERSSTv5 anomalies (1991-2020), last 60 months
    forecast  NCEP CFSv2 ensemble (NMME real-time anomalies, 9 months) + NMME model means

Oscillations (panel only)
  AO, NAO, PNA, SAM  NOAA CPC daily indices + CPC's GEFS 31-member 0-15 day forecasts
  AAM                global relative AAM from GEFS analyses / 31-member forecast (aam.py)
  AMO, PDO, PMM      ERSSTv5 monthly + CFSv2 ensemble (sst_indices.py, patterns.json)

Usage:  python pipeline/modes_pipeline.py --out public/modes.json [--cache .cache]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import aam
from common import download, http_get, log, month_add, opendap_ascii, opendap_size, rnd, utcnow, ym_str
from ersst import anomalies, climatology, load_ersst, ocean_mask
from sst_indices import compute_indices, load_patterns

PSL = 'https://psl.noaa.gov/thredds/dodsC/Datasets'
OISST = PSL + '/noaa.oisst.v2.highres/sst.day.anom.{year}.nc'
NMME = 'https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom'
NMME_MEMBERS_MODEL = 'CFSv2'
NMME_MEAN_MODELS = ['NMME', 'CanESM5', 'GEM5.2_NEMO', 'NASA_GEOS5v2', 'NCAR_CESM1', 'NCAR_CCSM4', 'GFDL_SPEAR']
CPC_TELE = 'https://ftp.cpc.ncep.noaa.gov/cwlinks'
TELE = {
    # id: (cdas observed file, gefs forecast file, csv column)
    'ao': ('norm.daily.ao.cdas.z1000.19500101_current.csv', 'norm.daily.ao.gefs.z1000.120days.csv', 'ao'),
    'nao': ('norm.daily.nao.cdas.z500.19500101_current.csv', 'norm.daily.nao.gefs.z500.120days.csv', 'nao'),
    'pna': ('norm.daily.pna.cdas.z500.19500101_current.csv', 'norm.daily.pna.gefs.z500.120days.csv', 'pna'),
    'sam': ('norm.daily.aao.cdas.z700.19790101_current.csv', 'norm.daily.aao.gefs.z700.120days.csv', 'aao'),
}
ONI_URL = 'https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt'
PDO_URL = 'https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat'

DAILY_DAYS = 150
MONTHLY_MONTHS = 60
TELE_DAYS = 120

# (south, north, west, east) boxes on the OISST 0.25 degree grid
OISST_BOXES = {
    'nino34': (-5, 5, 190, 240),
    'nino3': (-5, 5, 210, 270),
    'nino4': (-5, 5, 160, 210),
    'nino12': (-10, 0, 270, 280),
    'iod_w': (-10, 10, 50, 70),
    'iod_e': (-10, 0, 90, 110),
    'atl3': (-3, 3, 340, 360),
}
SST_KEYS = ['nino34', 'nino3', 'nino4', 'nino12', 'dmi', 'iod_w', 'iod_e', 'atl3', 'amo', 'pdo', 'pmm']


def rlist(values, nd: int = 2) -> list:
    return [rnd(v, nd) for v in values]


# --------------------------------------------------------------------------------------
# OISST daily box means
# --------------------------------------------------------------------------------------

def oisst_daily(days: int) -> dict:
    end_guess = utcnow().date()
    start = end_guess - dt.timedelta(days=days + 10)
    series: dict[str, dict[dt.date, float]] = {k: {} for k in OISST_BOXES}
    for year in range(start.year, end_guess.year + 1):
        url = OISST.format(year=year)
        try:
            n = opendap_size(url, 'time')
        except Exception as e:
            log(f'OISST {year}: {e}')
            continue
        jan1 = dt.date(year, 1, 1)
        t0 = max(0, (start - jan1).days)
        t1 = n - 1
        if t0 > t1:
            continue
        log(f'OISST {year}: days {t0}..{t1}')

        def box(key: str, url=url, t0=t0, t1=t1):
            s, nn, w, e = OISST_BOXES[key]
            i0 = math.ceil((s + 89.875) / 0.25)
            i1 = math.floor((nn + 89.875) / 0.25)
            j0 = math.ceil((w - 0.125) / 0.25)
            j1 = min(math.floor((e - 0.125) / 0.25), 1439)
            # every 2nd point (0.5 degree) is plenty for a box mean
            a = opendap_ascii(url, f'anom[{t0}:1:{t1}][{i0}:2:{i1}][{j0}:2:{j1}]')
            lats = -89.875 + 0.25 * np.arange(i0, i1 + 1, 2)
            w8 = np.cos(np.deg2rad(lats))[None, :, None] * np.ones_like(a)
            ok = np.isfinite(a)
            return np.where(ok, a * w8, 0).sum(axis=(1, 2)) / np.where(ok, w8, 0).sum(axis=(1, 2))

        with ThreadPoolExecutor(len(OISST_BOXES)) as pool:
            results = dict(zip(OISST_BOXES, pool.map(box, OISST_BOXES)))
        for key, vals in results.items():
            for k, v in enumerate(vals):
                series[key][jan1 + dt.timedelta(days=t0 + k)] = float(v)
    dates = sorted(set.intersection(*(set(s) for s in series.values())))[-days:]
    out = {k: [series[k][d] for d in dates] for k in OISST_BOXES}
    out['dmi'] = [w - e for w, e in zip(out['iod_w'], out['iod_e'])]
    log(f'OISST daily: {dates[0]}..{dates[-1]}')
    return {
        'source': 'NOAA OISST v2.1 (daily anomalies vs 1991-2020)',
        'dates': [d.isoformat() for d in dates],
        'series': {k: rlist(v) for k, v in out.items()},
    }


# --------------------------------------------------------------------------------------
# ERSST monthly + CFSv2 / NMME seasonal forecasts
# --------------------------------------------------------------------------------------

def mask_ice(anom: np.ndarray, months: list[tuple[int, int]], clim: np.ndarray) -> np.ndarray:
    out = anom.copy()
    for k, (_, m) in enumerate(months):
        out[k][~ocean_mask(clim, m)] = np.nan
    return out


def nmme_dirs(model: str) -> list[str]:
    html = http_get(f'{NMME}/{model}/').text
    return sorted(set(re.findall(r'href="(\d{10})/"', html)))


def nmme_targets(ds) -> list[tuple[int, int]]:
    """Target months from 'months since 1960-01-..' values."""
    out = []
    for t in np.asarray(ds['target'][:]):
        k = int(math.floor(float(t) + 1e-6))
        out.append((1960 + k // 12, k % 12 + 1))
    return out


def to_ersst_grid(field: np.ndarray) -> np.ndarray:
    """(..., 181, 360) 1-degree (90N first, lon 0..359) -> (..., 89, 180) ERSST points."""
    return field[..., 2:179:2, 0:360:2]


def seasonal_forecasts(cache: Path, clim: np.ndarray, patterns: dict) -> dict:
    import netCDF4

    d = nmme_dirs(NMME_MEMBERS_MODEL)[-1]
    yyyymm = d[:6]
    fname = f'{NMME_MEMBERS_MODEL}.tmpsfc.{yyyymm}.anom.nc'
    path = download(f'{NMME}/{NMME_MEMBERS_MODEL}/{d}/{fname}', cache / 'nmme' / fname)
    with netCDF4.Dataset(path) as ds:
        targets = nmme_targets(ds)
        f = np.asarray(ds['fcst'][:].filled(np.nan) if hasattr(ds['fcst'][:], 'filled') else ds['fcst'][:])
    f = to_ersst_grid(f.astype(np.float64))  # (members, leads, 89, 180)
    f[np.abs(f) > 1e10] = np.nan
    for k, (_, m) in enumerate(targets):
        f[:, k][:, ~ocean_mask(clim, m)] = np.nan
    idx = compute_indices(f, patterns)  # each (members, leads)
    members = {k: [rlist(row) for row in idx[k]] for k in SST_KEYS}
    mean = {k: rlist(np.nanmean(idx[k], axis=0)) for k in SST_KEYS}
    log(f'CFSv2 {yyyymm}: {f.shape[0]} members x {f.shape[1]} months {ym_str(targets[0])}..{ym_str(targets[-1])}')

    models = {}
    for model in NMME_MEAN_MODELS:
        mname = f'{model}.tmpsfc.{yyyymm}.ENSMEAN.anom.nc'
        try:
            p = download(f'{NMME}/ENSMEAN/{d}/{mname}', cache / 'nmme' / mname)
            with netCDF4.Dataset(p) as ds:
                t = nmme_targets(ds)
                g = np.asarray(ds['fcst'][:], dtype=np.float64)
        except Exception as e:
            log(f'NMME {model} {yyyymm}: not available ({e.__class__.__name__})')
            continue
        g = to_ersst_grid(g)
        g[np.abs(g) > 1e10] = np.nan
        for k, (_, m) in enumerate(t):
            g[k][~ocean_mask(clim, m)] = np.nan
        gi = compute_indices(g, patterns)
        # align on the CFSv2 target months
        models[model] = {
            k: [rnd(gi[k][t.index(ym)]) if ym in t else None for ym in targets] for k in SST_KEYS
        }
    log(f'NMME model means: {", ".join(models)}')
    for old in (cache / 'nmme').glob('*.nc'):
        if f'.{yyyymm}.' not in old.name:
            old.unlink()  # previous months' forecasts

    return {
        'model': 'NCEP CFSv2',
        'source': 'NOAA CPC NMME real-time anomalies (vs 1991-2020 hindcasts)',
        'init': f'{yyyymm[:4]}-{yyyymm[4:]}',
        'months': [ym_str(t) for t in targets],
        'members': members,
        'mean': mean,
        'models': models,
    }


def official_monthly(months: list[str]) -> dict:
    out = {}
    seas = ['DJF', 'JFM', 'FMA', 'MAM', 'AMJ', 'MJJ', 'JJA', 'JAS', 'ASO', 'SON', 'OND', 'NDJ']
    try:
        oni = {}
        for line in http_get(ONI_URL).text.splitlines()[1:]:
            p = line.split()
            if len(p) == 4 and p[0] in seas:
                oni[f'{int(p[1]):04d}-{seas.index(p[0]) + 1:02d}'] = float(p[3])
        out['oni'] = {
            'name': 'ONI (CPC, 3-month mean)',
            'values': [oni.get(m) for m in months],
        }
    except Exception as e:
        log(f'ONI not available: {e}')
    try:
        pdo = {}
        for line in http_get(PDO_URL).text.splitlines()[2:]:
            p = line.split()
            if len(p) == 13 and p[0].isdigit():
                for k, v in enumerate(p[1:]):
                    if abs(float(v)) < 90:
                        pdo[f'{int(p[0]):04d}-{k + 1:02d}'] = float(v)
        out['pdo'] = {'name': 'NCEI ERSSTv5 PDO', 'values': [pdo.get(m) for m in months]}
    except Exception as e:
        log(f'NCEI PDO not available: {e}')
    return out


def monthly_obs(cache: Path, patterns: dict) -> tuple[dict, np.ndarray]:
    months, sst = load_ersst(cache)
    clim = climatology(months, sst)
    sel = list(range(len(months) - MONTHLY_MONTHS, len(months)))
    sel_months = [months[k] for k in sel]
    anom = mask_ice(anomalies(sel_months, sst[sel], clim), sel_months, clim)
    idx = compute_indices(anom, patterns)
    labels = [ym_str(m) for m in sel_months]
    log(f'ERSST monthly: {labels[0]}..{labels[-1]}')
    return (
        {
            'source': 'NOAA ERSSTv5 (monthly anomalies vs 1991-2020)',
            'months': labels,
            'series': {k: rlist(idx[k]) for k in SST_KEYS},
            'official': official_monthly(labels),
        },
        clim,
    )


# --------------------------------------------------------------------------------------
# CPC teleconnection indices (observed + GEFS)
# --------------------------------------------------------------------------------------

def cpc_teleconnection(key: str) -> dict:
    obs_file, fc_file, col = TELE[key]
    rows = list(csv.DictReader(io.StringIO(http_get(f'{CPC_TELE}/{obs_file}').text)))
    obs = []
    for r in rows:
        try:
            v = float(r[f'{col}_index_cdas'])
        except (ValueError, KeyError):
            continue
        if math.isfinite(v):
            obs.append((dt.date(int(r['year']), int(r['month']), int(r['day'])), v))
    obs = obs[-TELE_DAYS:]

    fc = list(csv.DictReader(io.StringIO(http_get(f'{CPC_TELE}/{fc_file}').text)))
    init = max(r['time'] for r in fc)
    latest = [r for r in fc if r['time'] == init]
    leads = sorted({int(r['lead']) for r in latest})
    mems = sorted({int(r['member']) for r in latest})
    grid = np.full((len(mems), len(leads)), np.nan)
    dates = [''] * len(leads)
    for r in latest:
        i = mems.index(int(r['member']))
        j = leads.index(int(r['lead']))
        grid[i, j] = float(r[f'{col}_index'])
        dates[j] = r['valid_time']
    log(f'{key.upper()}: obs through {obs[-1][0]}, GEFS init {init} ({len(mems)} members, {len(leads)} leads)')
    return {
        'obs': {
            'source': 'NOAA CPC (CDAS) daily index',
            'dates': [d.isoformat() for d, _ in obs],
            'values': rlist([v for _, v in obs]),
        },
        'forecast': {
            'model': 'GEFS',
            'source': 'NOAA CPC GEFS ensemble index forecast',
            'init': init,
            'dates': dates,
            'members': [rlist(row) for row in grid],
            'mean': rlist(np.nanmean(grid, axis=0)),
        },
    }


def aam_index(cache: Path | None, pool: ThreadPoolExecutor) -> dict:
    res = aam.build(cache, pool)
    members = res['members']
    return {
        'sigma': res['sigma'],
        'obs': {
            'source': 'GEFS control 00Z analyses, anomaly vs NCEP/NCAR R1 1991-2020',
            'dates': [d.isoformat() for d, _ in res['hist']],
            'values': rlist([v for _, v in res['hist']]),
        },
        'forecast': {
            'model': 'GEFS',
            'source': 'GEFS 31-member ensemble, 00Z valid times',
            'init': res['init'],
            'dates': res['dates'],
            'members': [rlist(row) for row in members],
            'mean': rlist(members.mean(axis=0)),
        },
    }


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def safe(name: str, fn, *args):
    """Run one section; a failing source must not take the others down."""
    try:
        return fn(*args)
    except Exception as e:
        log(f'!! {name} failed: {e.__class__.__name__}: {e}')
        return None


def run(out_path: Path, cache: Path, workers: int = 24, skip_aam: bool = False) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    patterns = load_patterns()

    monthly, clim = monthly_obs(cache, patterns)
    data = {
        'version': 1,
        'generated': utcnow().strftime('%Y-%m-%dT%H:%MZ'),
        'daily': safe('OISST daily', oisst_daily, DAILY_DAYS),
        'monthly': monthly,
        'seasonal': safe('CFSv2 / NMME', seasonal_forecasts, cache, clim, patterns),
        'tele': {},
        'validation': json.loads(Path(__file__).with_name('patterns.json').read_text()).get('validation'),
    }
    for key in TELE:
        data['tele'][key] = safe(key, cpc_teleconnection, key)
    if not skip_aam:
        with ThreadPoolExecutor(workers) as pool:
            data['tele']['aam'] = safe('AAM', aam_index, cache, pool)

    # keep yesterday's values for any section that failed today
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text())
            for k in ('daily', 'seasonal'):
                if data[k] is None and old.get(k):
                    data[k] = old[k]
            for k, v in data['tele'].items():
                if v is None and old.get('tele', {}).get(k):
                    data['tele'][k] = old['tele'][k]
        except Exception:
            pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, separators=(',', ':'), allow_nan=False))
    log(f'wrote {out_path} ({out_path.stat().st_size / 1024:.1f} kB)')
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=Path, default=Path('public/modes.json'))
    p.add_argument('--cache', type=Path, default=Path('.cache'))
    p.add_argument('--workers', type=int, default=24)
    p.add_argument('--skip-aam', action='store_true', help='skip the GEFS AAM section (slow)')
    args = p.parse_args()
    run(args.out, args.cache, args.workers, args.skip_aam)


if __name__ == '__main__':
    main()
