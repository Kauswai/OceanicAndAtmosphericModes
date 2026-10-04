#!/usr/bin/env python3
"""
One-off: GEFS-analysis minus NCEP/NCAR R1 relative AAM offset (writes aam_calibration.json).

R1 (whose 1991-2020 climatology the AAM anomaly uses) stopped updating in March 2026, so
the offset is fitted over 1 Jan - 14 Mar 2026, when both are available. Days compared:
GEFS control 00Z analysis vs R1 daily mean (zonal means from every 2nd R1 longitude).

Usage:  python pipeline/calibrate_aam.py [--cache .cache]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from aam import CALIBRATION_PATH, LEVELS, R1_LEVELS, UNIT, AamReader, aam_from_zonal_mean
from common import log, opendap_ascii

R1_DAILY = 'https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis/Dailies/pressure/uwnd.2026.nc'
START = dt.date(2026, 1, 1)
DAYS = 73


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cache', type=Path, default=Path('.cache'))
    args = p.parse_args()

    days = [START + dt.timedelta(days=k) for k in range(DAYS)]
    lev_idx = [R1_LEVELS.index(lv) for lv in LEVELS]
    lats = np.arange(90, -90.1, -2.5)
    r1 = []
    for k0 in range(0, DAYS, 5):
        k1 = min(k0 + 4, DAYS - 1)
        log(f'R1 daily {days[k0]}..{days[k1]}')
        u = opendap_ascii(R1_DAILY, f'uwnd[{k0}:1:{k1}][0:1:16][0:1:72][0:2:143]')
        r1 += [aam_from_zonal_mean(u[t][lev_idx].mean(axis=2), lats) for t in range(u.shape[0])]
    r1 = np.array(r1)

    reader = AamReader(args.cache / 'aam')
    with ThreadPoolExecutor(16) as pool:
        gefs = np.array(
            list(pool.map(lambda d: reader.aam(dt.datetime(d.year, d.month, d.day), 'gec00', 0), days))
        )

    diff = gefs - r1
    r = float(np.corrcoef(gefs, r1)[0, 1])
    offset = float(diff.mean())
    log(f'GEFS - R1: mean {offset / UNIT:.3f}e25, std {diff.std() / UNIT:.3f}e25, r = {r:.3f}')
    CALIBRATION_PATH.write_text(
        json.dumps(
            {
                'offset': offset,
                'period': f'{days[0]}..{days[-1]}',
                'r': round(r, 3),
                'diffStd': float(diff.std()),
                'note': 'GEFS control 00Z analysis minus NCEP/NCAR R1 daily mean, 12 levels',
            },
            indent=1,
        )
    )
    log(f'wrote {CALIBRATION_PATH}')


if __name__ == '__main__':
    main()
