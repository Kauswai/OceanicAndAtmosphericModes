# OceanicAndAtmosphericModes

Windy.com plugin showing the equatorial climate modes (ENSO, Indian Ocean Dipole, Atlantic
Niño) on the map and in an interactive panel, plus AO, NAO, PNA, SAM, AAM, PDO, AMO and PMM
graphs with GEFS / CFSv2 ensemble forecasts.

- Plugin + data pipeline: [windy-plugin-climate-modes/](windy-plugin-climate-modes/README.md)
- Daily data: <https://kauswai.github.io/OceanicAndAtmosphericModes/modes.json> (built by `.github/workflows/update-modes-data.yml`)
- Companion plugin: [MJO](https://github.com/Kauswai/MJO)

## Install in Windy (no local server)

Log in to Windy, then open:

**<https://www.windy.com/dev/kauswai.github.io/OceanicAndAtmosphericModes/plugin.js>**

Windy installs the plugin to your account and opens it. It stays in your Windy menu and
loads the latest build from GitHub Pages each time. A push to the plugin source rebuilds
`plugin.js` on Pages (`update-modes-data.yml`; on a push the data is kept, not recomputed). `npm start` + `windy.com/dev/localhost:9998/plugin.js` is only needed while developing.
