#!/usr/bin/env python3
"""
One-off fit of the PDO and PMM patterns used by modes_pipeline.py (writes patterns.json),
plus a validation of every SST index against the official series.

  PDO  pattern = regression of ERSSTv5 North Pacific anomalies onto the NCEI ERSST PDO index, 1950-2025; projection then linearly calibrated.
  PMM  per-point regression on the cold-tongue index (CTI) is removed first (as in
       Chiang & Vimont 2004), then the same regression / projection / calibration
       against the Chiang & Vimont PMM SST index.

Usage:  python pipeline/calibrate.py [--cache .cache]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from common import http_get, log
from ersst import anomalies, load_ersst
from sst_indices import LAT2D, LON2D, MASKS, PATTERNS_PATH, WEIGHTS, box_mean, compute_indices

PDO_URL = 'https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat'
PMM_URL = 'https://www.aos.wisc.edu/dvimont/MModes/RealTime/PMM.txt'
ONI_URL = 'https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt'
DMI_URL = 'https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data'
AMO_URL = 'https://psl.noaa.gov/data/correlation/amon.us.data'

FIT = (1950, 2025)


def parse_table(text: str, missing: float, skip: int = 1) -> dict[tuple[int, int], float]:
    """Year + 12 monthly columns."""
    out = {}
    for line in text.splitlines()[skip:]:
        p = line.split()
        if len(p) != 13:
            continue
        try:
            y = int(p[0])
            vals = [float(v) for v in p[1:]]
        except ValueError:
            continue
        for m, v in enumerate(vals):
            if abs(v - missing) > 1e-3 and abs(v) < 90:
                out[(y, m + 1)] = v
    return out


def official_series() -> dict[str, dict]:
    pdo = parse_table(http_get(PDO_URL).text, 99.99, skip=2)
    pmm = {}
    for line in http_get(PMM_URL).text.splitlines()[1:]:
        p = line.split()
        if len(p) >= 3:
            pmm[(int(p[0]), int(p[1]))] = float(p[2])
    seas = ['DJF', 'JFM', 'FMA', 'MAM', 'AMJ', 'MJJ', 'JJA', 'JAS', 'ASO', 'SON', 'OND', 'NDJ']
    oni = {}
    for line in http_get(ONI_URL).text.splitlines()[1:]:
        p = line.split()
        if len(p) == 4 and p[0] in seas:
            oni[(int(p[1]), seas.index(p[0]) + 1)] = float(p[3])  # centre month
    dmi = parse_table(http_get(DMI_URL).text, -9999.0)
    amo = parse_table(http_get(AMO_URL).text, -99.99)
    return {'pdo': pdo, 'pmm': pmm, 'oni': oni, 'dmi': dmi, 'amo': amo}


def fit_pattern(x: np.ndarray, y: np.ndarray, mask: np.ndarray):
    """Regression map of x (t, lat, lon) on standardised y (t), inside mask."""
    z = (y - y.mean()) / y.std()
    pat = np.full(mask.shape, np.nan)
    xm = x[:, mask]
    good = np.isfinite(xm).all(axis=0)  # ignore points with gaps (sea ice)
    xm = xm - np.nanmean(xm, axis=0)
    reg = (xm * z[:, None]).mean(axis=0)
    vals = np.where(good, reg, np.nan)
    pat[mask] = vals
    return pat


def calib(proj: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    a, b = np.polyfit(proj, y, 1)
    r = np.corrcoef(proj, y)[0, 1]
    return float(a), float(b), float(r)


def raw_projection(x: np.ndarray, field: np.ndarray) -> np.ndarray:
    m = np.isfinite(field)
    a = x[:, m]
    p = field[m]
    w = WEIGHTS[m]
    ok = np.isfinite(a)
    return np.where(ok, a * p * w, 0).sum(-1) / np.where(ok, p * p * w, 0).sum(-1)


def points(field: np.ndarray, beta: np.ndarray | None = None) -> list:
    out = []
    for i, j in zip(*np.where(np.isfinite(field))):
        row = [float(LAT2D[i, j]), float(LON2D[i, j]), round(float(field[i, j]), 5)]
        if beta is not None:
            row.append(round(float(beta[i, j]), 5) if np.isfinite(beta[i, j]) else 0.0)
        out.append(row)
    return out


def corr_report(name: str, ours: dict, ref: dict, period=(1982, 2025)):
    keys = [k for k in ref if k in ours and period[0] <= k[0] <= period[1]]
    a = np.array([ours[k] for k in keys])
    b = np.array([ref[k] for k in keys])
    r = np.corrcoef(a, b)[0, 1]
    rmse = np.sqrt(np.mean((a - b) ** 2))
    log(f'{name:>10}: r = {r:.3f}, rmse = {rmse:.2f}, n = {len(keys)} ({period[0]}-{period[1]})')
    return round(float(r), 3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cache', type=Path, default=Path('.cache'))
    args = p.parse_args()

    months, sst = load_ersst(args.cache, max_age_hours=24 * 20)
    anom = anomalies(months, sst)
    ref = official_series()

    sel = [k for k, ym in enumerate(months) if FIT[0] <= ym[0] <= FIT[1]]
    fit_months = [months[k] for k in sel]
    x = anom[sel]

    # ---- PDO
    keys = [k for k, ym in enumerate(fit_months) if ym in ref['pdo']]
    y = np.array([ref['pdo'][fit_months[k]] for k in keys])
    xp = x[keys]
    pdo_field = fit_pattern(xp, y, MASKS['pdo'])
    a, b, r = calib(raw_projection(xp, pdo_field), y)
    log(f'PDO fit: r = {r:.3f} (a = {a:.3f}, b = {b:.3f})')
    pdo = {'a': a, 'b': b, 'r': round(r, 3), 'points': points(pdo_field)}

    # ---- PMM: remove the CTI-regressed part at each point, then fit
    # minus the 60S-60N mean so the global warming trend does not leak into the PMM
    x = x - box_mean(x, 'glob60')[:, None, None]
    cti = box_mean(x, 'cti')
    c = cti - cti.mean()
    xm = x - np.nanmean(x, axis=0)
    beta = np.nansum(xm * c[:, None, None], axis=0) / np.sum(c * c)
    beta[~MASKS['pmm']] = np.nan
    resid = x - beta * cti[:, None, None]
    keys = [k for k, ym in enumerate(fit_months) if ym in ref['pmm']]
    y = np.array([ref['pmm'][fit_months[k]] for k in keys])
    pmm_field = fit_pattern(resid[keys], y, MASKS['pmm'])
    a2, b2, r2 = calib(raw_projection(resid[keys], pmm_field), y)
    log(f'PMM fit: r = {r2:.3f} (a = {a2:.3f}, b = {b2:.3f})')
    pmm = {'a': a2, 'b': b2, 'r': round(r2, 3), 'points': points(pmm_field, beta)}

    PATTERNS_PATH.write_text(
        json.dumps(
            {
                'source': 'ERSSTv5 1950-2025, anomalies w.r.t. 1991-2020',
                'pdo': {**pdo, 'reference': 'NCEI ERSST v5 PDO'},
                'pmm': {**pmm, 'reference': 'Chiang & Vimont PMM SST index'},
            },
            separators=(',', ':'),
        )
    )
    log(f'wrote {PATTERNS_PATH}')

    # ---- validation of all indices with the fitted patterns
    from sst_indices import load_patterns

    idx = compute_indices(anom, load_patterns())
    series = {k: {ym: float(v[t]) for t, ym in enumerate(months)} for k, v in idx.items()}
    n34 = series['nino34']
    n34_3m = {
        ym: np.mean([n34.get((ym[0] + (ym[1] - 1 + d) // 12, (ym[1] - 1 + d) % 12 + 1), np.nan) for d in (-1, 0, 1)])
        for ym in n34
    }
    n34_3m = {k: v for k, v in n34_3m.items() if np.isfinite(v)}
    report = {
        'nino34_vs_oni': corr_report('Nino3.4/ONI', n34_3m, ref['oni']),
        'dmi_vs_hadisst': corr_report('DMI', series['dmi'], ref['dmi']),
        'amo_vs_psl': corr_report('AMO', series['amo'], ref['amo'], (1950, 2023)),
        'pdo_vs_ncei': corr_report('PDO', series['pdo'], ref['pdo'], (1950, 2026)),
        'pmm_vs_vimont': corr_report('PMM', series['pmm'], ref['pmm'], (1950, 2026)),
        'pdo_recent': corr_report('PDO 2000+', series['pdo'], ref['pdo'], (2000, 2026)),
        'pmm_recent': corr_report('PMM 2000+', series['pmm'], ref['pmm'], (2000, 2026)),
    }
    data = json.loads(PATTERNS_PATH.read_text())
    data['validation'] = report
    PATTERNS_PATH.write_text(json.dumps(data, separators=(',', ':')))


if __name__ == '__main__':
    main()
