# windy-plugin-climate-modes — equatorial modes & oscillations for Windy.com

A [Windy.com](https://www.windy.com) plugin with the state and ensemble forecasts of the
main climate modes. A companion to the [MJO plugin](https://github.com/Kauswai/MJO).

## What it shows

**Equatorial modes** (on the main map and in the panel)

| Mode | Index | Phase threshold |
| --- | --- | --- |
| ENSO | Niño 3.4 SST anomaly, 5°S–5°N 170°W–120°W (Niño 1+2 / 3 / 4 optional on the map) | ±0.5 °C (±1 moderate, ±1.5 strong, ±2 very strong) |
| Indian Ocean Dipole | DMI = 10°S–10°N 50–70°E minus 10°S–0° 90–110°E | ±0.4 °C |
| Atlantic Niño | ATL3, 3°S–3°N 20°W–0° | ±0.5 °C |

On the map each box is filled with its SST anomaly and labelled with the index and phase.
The map can show the **latest week** (daily OISST), the **latest month** (ERSSTv5) or any
**CFSv2 forecast month** (ensemble mean + share of members in each phase). Click a label
on the map to open that mode's graph. A button switches Windy's layer to sea temperature.

**Oscillations** (panel only)

| Index | Observed | Ensemble forecast |
| --- | --- | --- |
| AO, NAO, PNA, SAM (AAO) | NOAA CPC daily indices | NOAA CPC GEFS 31 members, 0–15 days |
| AAM (global relative angular momentum) | GEFS control analyses | GEFS 31 members, 0–16 days |
| PDO, AMO, PMM | ERSSTv5 monthly | NCEP CFSv2 32 members, 9 months (+ NMME model means) |

**Graphs** (click a card / button): observed record (red / blue fill above / below zero),
every ensemble member, the 10–90 % spread, the ensemble mean, NMME model means and the
official series (ONI, NCEI PDO) for comparison. Hover for values and member probabilities,
click a forecast step to select it: the bar under the graph shows the share of members in
each phase. For daily indices the selected day moves Windy's timeline (and the timeline
is drawn as a cyan line); for the equatorial modes it shows that month on the map.

## How it works

```
┌──────────────── GitHub Actions (twice daily) ──────────────┐       ┌──── windy.com ──────────┐
│ pipeline/modes_pipeline.py                                  │       │ windy-plugin-climate-   │
│  • NOAA OISST v2.1 daily anomalies (PSL OPeNDAP)            │       │ modes                   │
│  • NOAA ERSSTv5 monthly SST (PSL)                           │──────▶│  fetch modes.json       │
│  • NCEP CFSv2 + NMME real-time anomalies (CPC FTP)          │ Pages │  cards / graphs         │
│  • CPC AO/NAO/PNA/AAO observed + GEFS forecasts             │ (CORS)│  map boxes & labels     │
│  • GEFS U-wind, 12 levels → AAM (AWS open data)             │       │                         │
└─────────────────────────────────────────────────────────────┘       └─────────────────────────┘
```

None of these servers send CORS headers (and most forecasts are only published as
images), so a small pipeline turns them into one ~100 kB `modes.json` on GitHub Pages.

- **SST indices** are computed identically from ERSSTv5 (observed) and from every CFSv2
  member (NMME anomalies vs the model's own 1991–2020 hindcasts), on the ERSST 2° grid.
  Points that are ice-covered in the climatology are left out (model skin temperature over
  ice is not SST).
- **PDO / PMM** are projections onto patterns regressed onto the official indices
  (`pipeline/calibrate.py` → `patterns.json`); PMM first removes the local regression on the
  cold-tongue index, as in Chiang & Vimont (2004), after removing the 60°S–60°N mean so the warming trend does not leak in (otherwise recent values ran ~+2 too high).
- **AMO** uses the Trenberth & Shea (2006) definition: North Atlantic 0–60°N minus the
  60°S–60°N mean, which removes the global warming trend without arbitrary detrending.
- **AAM** = (2πa³/g) ∫∫ [u] cos²φ dφ dp on the 12 GEFS pressure levels; anomaly vs the
  NCEP/NCAR R1 1991–2020 monthly climatology (smoothed to a daily cycle) after a fixed
  GEFS−R1 offset fitted over Jan–Mar 2026 (`pipeline/calibrate_aam.py`; r = 0.98, offset
  −0.12×10²⁵ kg m² s⁻¹). Lines at ±1σ = 1.2×10²⁵ (Weickmann & Berry).

**Verification** (`pipeline/calibrate.py`, values also shown in the plugin):

| Index | Compared with | r |
| --- | --- | --- |
| Niño 3.4 (3-month mean) | CPC ONI 1982–2025 | 0.993 |
| PDO | NCEI ERSSTv5 PDO 1950–2026 | 0.981 |
| PMM | Chiang & Vimont PMM SST 1950–2026 | 0.932 (0.951 since 2000) |
| DMI | HadISST DMI (PSL) 1982–2025 | 0.822 (different SST analysis) |
| AMO | PSL (Enfield, Kaplan SST, detrended) 1950–2023 | 0.783 (different definition) |

## Setup

### 1. Publish the data (GitHub Pages)

The workflows live at the repository root (`.github/workflows/`) and run inside
`windy-plugin-climate-modes/`.

1. The repository must be **public** (GitHub Pages on free accounts needs that).
2. *Settings → Pages → Build and deployment → Source: **GitHub Actions***.
3. *Actions → update-modes-data → Run workflow* (it then runs daily at 07:10 and 14:30 UTC).
   The first run downloads ~1.5 GB (GEFS, ERSST, NMME), ~10–15 min; later runs use the cache.
4. The data is then at <https://kauswai.github.io/OceanicAndAtmosphericModes/modes.json>, which is already
   the plugin's `DEFAULT_DATA_URL` ([src/modes.ts](src/modes.ts)). It can be changed in the
   plugin under *Data source*.

### 2. Develop the plugin

```bash
npm i
npm run data      # optional: build public/modes.json locally (Python + pipeline/requirements.txt)
npm start         # serves https://localhost:9999/plugin.js (+ modes.json)
```

Open <https://localhost:9999/plugin.js> once and accept the self-signed certificate, then go
to <https://www.windy.com/developer-mode> and load `https://localhost:9999/plugin.js`.
Without a configured data URL the plugin falls back to `https://localhost:9999/modes.json`.
`python pipeline/modes_pipeline.py --skip-aam` skips the slow GEFS AAM part.

On Windows use `npm run build:win` instead of `npm run build`.

### 3. Publish the plugin

Add a `WINDY_API_KEY` repository secret and run the **publish-plugin** workflow (or
see <https://docs.windy-plugins.com/>). Optionally add `src/screenshot.jpg` for the gallery.

## Pipeline files

| File | Purpose |
| --- | --- |
| `pipeline/modes_pipeline.py` | daily job → `modes.json` |
| `pipeline/sst_indices.py` | index regions and formulas (shared by obs and forecasts) |
| `pipeline/aam.py` | GEFS relative AAM |
| `pipeline/calibrate.py` | fits `patterns.json` (PDO, PMM) and validates all SST indices (run once) |
| `pipeline/calibrate_aam.py` | fits `aam_calibration.json` (run once) |

## Data sources & credits

- NOAA **OISST v2.1** and **ERSSTv5**, via NOAA PSL
- **NCEP CFSv2** and the **North American Multi-Model Ensemble** (CanESM5, GEM5.2-NEMO,
  NASA GEOS-S2S, NCAR CESM1 / CCSM4), real-time anomalies from NOAA CPC
- NOAA **CPC** AO, NAO, PNA and AAO indices and their GEFS forecasts
- NOAA **GEFS** via the [NOAA Open Data Dissemination program on AWS](https://registry.opendata.aws/noaa-gefs/)
- NCEP/NCAR Reanalysis 1 climatology, NOAA PSL
- Reference indices: CPC ONI, NCEI PDO, D. Vimont's PMM, PSL DMI / AMO
- Chiang & Vimont (2004) *J. Climate* 17, 4143; Trenberth & Shea (2006) *GRL* 33, L12704;
  Saji et al. (1999) *Nature* 401, 360; Weickmann & Berry (2007) *MWR* 135, 2075

`modes.json`: `daily {dates, series{nino34,…,dmi,atl3}}`, `monthly {months, series, official}`,
`seasonal {init, months, members{key: [member][lead]}, mean, models{model: {key: [lead]}}}`,
`tele {ao|nao|pna|sam|aam: {obs {dates, values}, forecast {init, dates, members, mean}}}`.
