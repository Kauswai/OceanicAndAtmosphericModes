"""NOAA ERSSTv5 monthly SST (2-degree), anomalies w.r.t. 1991-2020."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from common import download

ERSST_FILE = 'https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc'

# Points colder than this in the monthly climatology are (partly) ice covered; their
# "SST" is the freezing point in ERSST but ice-surface temperature in model skin
# temperature, so they are left out of every index.
ICE_CLIM_SST = -1.0


def load_ersst(cache: Path, max_age_hours: float = 20) -> tuple[list[tuple[int, int]], np.ndarray]:
    """Months (year, month) since Jan 1854 and SST (t, 89, 180), land = NaN."""
    import netCDF4

    path = download(ERSST_FILE, cache / 'ersst.v5.sst.mnmean.nc', max_age_hours=max_age_hours)
    with netCDF4.Dataset(path) as ds:
        sst = np.asarray(ds['sst'][:].filled(np.nan), dtype=np.float64)
    months = [(1854 + k // 12, k % 12 + 1) for k in range(sst.shape[0])]
    return months, sst


def climatology(months, sst) -> np.ndarray:
    """(12, 89, 180) 1991-2020 monthly mean."""
    clim = np.full((12,) + sst.shape[1:], np.nan)
    for m in range(12):
        idx = [k for k, (y, mm) in enumerate(months) if mm == m + 1 and 1991 <= y <= 2020]
        with np.errstate(invalid='ignore'):
            clim[m] = np.nanmean(sst[idx], axis=0)
    return clim


def anomalies(months, sst, clim: np.ndarray | None = None) -> np.ndarray:
    clim = climatology(months, sst) if clim is None else clim
    return sst - clim[[mm - 1 for _, mm in months]]


def ocean_mask(clim: np.ndarray, month: int) -> np.ndarray:
    """True for ice-free ocean points in calendar `month` (1-12)."""
    c = clim[month - 1]
    return np.isfinite(c) & (c > ICE_CLIM_SST)
