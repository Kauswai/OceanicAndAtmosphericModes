import type { ExternalPluginConfig } from '@windy/interfaces';

const config: ExternalPluginConfig = {
    name: 'windy-plugin-climate-modes',
    version: '1.0.0',
    icon: '🌊',
    title: 'Climate modes & oscillations',
    description:
        'ENSO, Indian Ocean Dipole and Atlantic Niño on the map, plus AO, NAO, PNA, SAM, AAM, ' +
        'PDO, AMO and PMM graphs with GEFS / CFSv2 ensemble forecasts.',
    author: 'Kauswai',
    repository: 'https://github.com/Kauswai/ClimateModes',
    desktopUI: 'rhpane',
    desktopWidth: 460,
    mobileUI: 'fullscreen',
    routerPath: '/climate-modes',
    private: true,
};

export default config;
