/**
 * Data model of modes.json (written by pipeline/modes_pipeline.py), the definitions of
 * every mode / oscillation, and helpers shared by the panel, the chart and the map layer.
 */

export const DEFAULT_DATA_URL = 'https://kauswai.github.io/ClimateModes/modes.json';

/** Served by `npm start` (rollup dev server) from public/modes.json */
export const DEV_DATA_URL = 'https://localhost:9999/modes.json';

const DATA_URL_STORAGE_KEY = 'windy-plugin-climate-modes:data-url';

type Num = number | null;

export interface DailyBlock {
    source: string;
    dates: string[];
    series: Record<string, Num[]>;
}

export interface MonthlyBlock {
    source: string;
    months: string[];
    series: Record<string, Num[]>;
    official: Record<string, { name: string; values: Num[] }>;
}

export interface SeasonalBlock {
    model: string;
    source: string;
    init: string;
    months: string[];
    members: Record<string, Num[][]>;
    mean: Record<string, Num[]>;
    models: Record<string, Record<string, Num[]>>;
}

export interface TeleBlock {
    sigma?: number;
    obs: { source: string; dates: string[]; values: Num[] };
    forecast: {
        model: string;
        source: string;
        init: string;
        dates: string[];
        members: Num[][];
        mean: Num[];
    };
}

export interface ModesData {
    version: number;
    generated: string;
    daily: DailyBlock | null;
    monthly: MonthlyBlock;
    seasonal: SeasonalBlock | null;
    tele: Record<string, TeleBlock | null>;
    validation?: Record<string, number>;
}

export type Group = 'equatorial' | 'oscillation';

export interface ModeDef {
    id: string;
    /** series key in daily / monthly / seasonal blocks, or tele key */
    key: string;
    group: Group;
    short: string;
    name: string;
    unit: string;
    /** time step of the main record */
    freq: 'daily' | 'monthly';
    /** |value| >= threshold -> positive / negative phase */
    threshold: number;
    /** further lines drawn on the chart (strong, very strong ...) */
    levels: number[];
    pos: string;
    neg: string;
    neutral: string;
    description: string;
    /** official series in monthly.official to overlay */
    official?: string;
}

export const MODES: ModeDef[] = [
    {
        id: 'enso',
        key: 'nino34',
        group: 'equatorial',
        short: 'ENSO',
        name: 'ENSO · Niño 3.4',
        unit: '°C',
        freq: 'monthly',
        threshold: 0.5,
        levels: [1, 1.5, 2],
        pos: 'El Niño',
        neg: 'La Niña',
        neutral: 'ENSO-neutral',
        description:
            'Sea-surface temperature anomaly in the Niño 3.4 box (5°S–5°N, 170°W–120°W). ' +
            'Above +0.5 °C El Niño, below −0.5 °C La Niña (±1 moderate, ±1.5 strong, ±2 very strong).',
        official: 'oni',
    },
    {
        id: 'iod',
        key: 'dmi',
        group: 'equatorial',
        short: 'IOD',
        name: 'Indian Ocean Dipole · DMI',
        unit: '°C',
        freq: 'monthly',
        threshold: 0.4,
        levels: [0.8],
        pos: 'Positive IOD',
        neg: 'Negative IOD',
        neutral: 'IOD-neutral',
        description:
            'Dipole Mode Index: SST anomaly of the western pole (10°S–10°N, 50–70°E) minus the ' +
            'eastern pole (10°S–0°, 90–110°E). Beyond ±0.4 °C a positive / negative IOD (BoM threshold).',
    },
    {
        id: 'atl',
        key: 'atl3',
        group: 'equatorial',
        short: 'Atl. Niño',
        name: 'Atlantic Niño · ATL3',
        unit: '°C',
        freq: 'monthly',
        threshold: 0.5,
        levels: [1],
        pos: 'Atlantic Niño',
        neg: 'Atlantic Niña',
        neutral: 'Neutral',
        description:
            'Atlantic equatorial mode: SST anomaly in the ATL3 box (3°S–3°N, 20°W–0°). ' +
            'Warm events (Atlantic Niño) weaken the West African monsoon and shift rain over the Gulf of Guinea.',
    },
    {
        id: 'ao',
        key: 'ao',
        group: 'oscillation',
        short: 'AO',
        name: 'Arctic Oscillation',
        unit: 'σ',
        freq: 'daily',
        threshold: 0.5,
        levels: [1, 2],
        pos: 'Positive AO',
        neg: 'Negative AO',
        neutral: 'Neutral',
        description:
            'Leading mode of 1000 hPa height north of 20°N (NOAA CPC). Negative AO: weaker polar vortex, ' +
            'cold air outbreaks into mid-latitudes; positive AO: cold air locked in the Arctic.',
    },
    {
        id: 'nao',
        key: 'nao',
        group: 'oscillation',
        short: 'NAO',
        name: 'North Atlantic Oscillation',
        unit: 'σ',
        freq: 'daily',
        threshold: 0.5,
        levels: [1, 2],
        pos: 'Positive NAO',
        neg: 'Negative NAO',
        neutral: 'Neutral',
        description:
            'Pressure seesaw between Iceland and the Azores (500 hPa, NOAA CPC). Positive: stormy, mild ' +
            'N. Europe; negative: blocking, cold N. Europe and eastern N. America.',
    },
    {
        id: 'pna',
        key: 'pna',
        group: 'oscillation',
        short: 'PNA',
        name: 'Pacific–North American pattern',
        unit: 'σ',
        freq: 'daily',
        threshold: 0.5,
        levels: [1, 2],
        pos: 'Positive PNA',
        neg: 'Negative PNA',
        neutral: 'Neutral',
        description:
            'Wave train from the North Pacific over North America (500 hPa, NOAA CPC). Positive: ridge in ' +
            'the West, trough and cold in the East.',
    },
    {
        id: 'sam',
        key: 'sam',
        group: 'oscillation',
        short: 'SAM',
        name: 'Southern Annular Mode (AAO)',
        unit: 'σ',
        freq: 'daily',
        threshold: 0.5,
        levels: [1, 2],
        pos: 'Positive SAM',
        neg: 'Negative SAM',
        neutral: 'Neutral',
        description:
            'Leading mode of 700 hPa height south of 20°S (NOAA CPC AAO). Positive: westerlies contract ' +
            'towards Antarctica (drier S. Australia / NZ west coast); negative: westerlies shift north.',
    },
    {
        id: 'aam',
        key: 'aam',
        group: 'oscillation',
        short: 'AAM',
        name: 'Atmospheric angular momentum',
        unit: '10²⁵ kg m² s⁻¹',
        freq: 'daily',
        threshold: 0.6,
        levels: [1.2, 2.4],
        pos: 'Positive AAM',
        neg: 'Negative AAM',
        neutral: 'Near normal',
        description:
            'Global relative AAM anomaly (westerly wind momentum of the whole atmosphere, 1000–10 hPa). ' +
            'High AAM is El Niño-like (strong subtropical jets); low AAM La Niña-like. Lines at ±1σ, ±2σ.',
    },
    {
        id: 'pdo',
        key: 'pdo',
        group: 'oscillation',
        short: 'PDO',
        name: 'Pacific Decadal Oscillation',
        unit: '',
        freq: 'monthly',
        threshold: 0.5,
        levels: [1, 2],
        pos: 'Positive (warm) PDO',
        neg: 'Negative (cool) PDO',
        neutral: 'Neutral',
        description:
            'Leading pattern of North Pacific (20–70°N) SST. Negative PDO: cool NE Pacific edge, warm ' +
            'Kuroshio region; favours La Niña-like patterns. Values follow the NCEI ERSST PDO scale.',
        official: 'pdo',
    },
    {
        id: 'amo',
        key: 'amo',
        group: 'oscillation',
        short: 'AMO',
        name: 'Atlantic Multidecadal Oscillation',
        unit: '°C',
        freq: 'monthly',
        threshold: 0.1,
        levels: [0.2],
        pos: 'Warm AMO',
        neg: 'Cool AMO',
        neutral: 'Neutral',
        description:
            'North Atlantic (0–60°N, 80°W–0°) SST anomaly minus the 60°S–60°N mean (Trenberth & Shea ' +
            '2006), so the global warming trend is removed. Warm AMO: more Atlantic hurricanes, wetter Sahel.',
    },
    {
        id: 'pmm',
        key: 'pmm',
        group: 'oscillation',
        short: 'PMM',
        name: 'Pacific Meridional Mode',
        unit: '',
        freq: 'monthly',
        threshold: 1.7,
        levels: [3.4],
        pos: 'Positive PMM',
        neg: 'Negative PMM',
        neutral: 'Neutral',
        description:
            'NE-Pacific subtropical SST pattern with the cold-tongue (ENSO) signal removed (Chiang & ' +
            'Vimont 2004 scale). A positive PMM in spring often precedes El Niño. Lines at ±0.5σ, ±1σ.',
    },
];

export const MODE_BY_ID: Record<string, ModeDef> = Object.fromEntries(MODES.map(m => [m.id, m]));

export type Phase = 'pos' | 'neg' | 'neutral';

export const phaseOf = (mode: ModeDef, v: Num): Phase =>
    v === null || !Number.isFinite(v)
        ? 'neutral'
        : v >= mode.threshold
          ? 'pos'
          : v <= -mode.threshold
            ? 'neg'
            : 'neutral';

export const phaseLabel = (mode: ModeDef, v: Num): string => {
    const p = phaseOf(mode, v);
    return p === 'pos' ? mode.pos : p === 'neg' ? mode.neg : mode.neutral;
};

/** Strength wording for ENSO-like indices */
export function strengthOf(mode: ModeDef, v: Num): string {
    if (v === null || phaseOf(mode, v) === 'neutral') {
        return '';
    }
    const a = Math.abs(v);
    if (mode.id === 'enso') {
        return a >= 2 ? 'very strong' : a >= 1.5 ? 'strong' : a >= 1 ? 'moderate' : 'weak';
    }
    const strong = mode.levels[0];
    return a >= strong ? 'strong' : 'weak';
}

export const POS_COLOR = '#ff6b4a';
export const NEG_COLOR = '#4aa3ff';

/** Diverging colour for an anomaly, scaled so `full` gives the most saturated colour */
export function anomalyColor(v: Num, full: number): string {
    if (v === null || !Number.isFinite(v)) {
        return '#888888';
    }
    const t = Math.max(-1, Math.min(1, v / full));
    // white -> red / blue
    const [r, g, b] = t >= 0 ? [214, 47, 39] : [33, 102, 172];
    // square root: moderate anomalies are already clearly coloured
    const k = Math.sqrt(Math.abs(t));
    const mix = (c: number) => Math.round(245 + (c - 245) * k);
    const hex = (c: number) => mix(c).toString(16).padStart(2, '0');
    return `#${hex(r)}${hex(g)}${hex(b)}`;
}

export const fmt = (v: Num, nd = 2): string =>
    v === null || !Number.isFinite(v) ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(nd)}`;

export const formatDay = (iso: string): string => {
    const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', timeZone: 'UTC' });
};

export const formatMonth = (ym: string): string => {
    const d = new Date(`${ym.slice(0, 7)}-15T00:00:00Z`);
    return d.toLocaleDateString(undefined, { month: 'short', year: 'numeric', timeZone: 'UTC' });
};

/** ms timestamp of a YYYY-MM-DD (noon) or YYYY-MM (15th) label */
export const timeOf = (label: string): number =>
    label.length <= 7 ? Date.parse(`${label}-15T00:00:00Z`) : Date.parse(`${label.slice(0, 10)}T12:00:00Z`);

export const isoDay = (ts: number): string => new Date(ts).toISOString().slice(0, 10);

export const dayTimestamp = (iso: string): number => Date.parse(`${iso.slice(0, 10)}T12:00:00Z`);

// ----------------------------------------------------------------------------------------
// Unified series for one mode
// ----------------------------------------------------------------------------------------

export interface Point {
    t: number;
    label: string;
    v: number;
}

export interface ModeSeries {
    mode: ModeDef;
    /** main observed record */
    obs: Point[];
    obsSource: string;
    /** finer observed record (daily OISST for the SST modes) */
    obsDaily: Point[];
    official: { name: string; points: Point[] } | null;
    forecast: {
        model: string;
        source: string;
        init: string;
        labels: string[];
        times: number[];
        members: Num[][];
        mean: Num[];
        memberLabel: string;
    } | null;
    models: { name: string; values: Num[] }[];
    /** latest observed value and when */
    latest: Point | null;
    /** last 7-day mean of the daily record (SST modes) */
    latestWeek: Point | null;
}

const toPoints = (labels: string[], values: Num[]): Point[] =>
    labels
        .map((label, i) => ({ t: timeOf(label), label, v: values[i] as number }))
        .filter(p => p.v !== null && Number.isFinite(p.v));

export function seriesFor(data: ModesData, mode: ModeDef): ModeSeries {
    if (mode.freq === 'daily') {
        const tele = data.tele[mode.key];
        const obs = tele ? toPoints(tele.obs.dates, tele.obs.values) : [];
        return {
            mode,
            obs,
            obsSource: tele?.obs.source || '',
            obsDaily: [],
            official: null,
            forecast: tele
                ? {
                      model: tele.forecast.model,
                      source: tele.forecast.source,
                      init: tele.forecast.init,
                      labels: tele.forecast.dates,
                      times: tele.forecast.dates.map(timeOf),
                      members: tele.forecast.members,
                      mean: tele.forecast.mean,
                      memberLabel: 'GEFS member',
                  }
                : null,
            models: [],
            latest: obs.length ? obs[obs.length - 1] : null,
            latestWeek: null,
        };
    }

    const m = data.monthly;
    const obs = toPoints(m.months, m.series[mode.key] || []);
    const daily = data.daily && data.daily.series[mode.key] ? toPoints(data.daily.dates, data.daily.series[mode.key]) : [];
    const off = mode.official && m.official[mode.official];
    const s = data.seasonal;
    let latestWeek: Point | null = null;
    if (daily.length >= 7) {
        const last = daily.slice(-7);
        latestWeek = {
            t: last[last.length - 1].t,
            label: last[last.length - 1].label,
            v: last.reduce((a, p) => a + p.v, 0) / last.length,
        };
    }
    return {
        mode,
        obs,
        obsSource: m.source,
        obsDaily: daily,
        official: off ? { name: off.name, points: toPoints(m.months, off.values) } : null,
        forecast:
            s && s.members[mode.key]
                ? {
                      model: s.model,
                      source: s.source,
                      init: s.init,
                      labels: s.months,
                      times: s.months.map(timeOf),
                      members: s.members[mode.key],
                      mean: s.mean[mode.key],
                      memberLabel: 'CFSv2 member',
                  }
                : null,
        models: s
            ? Object.entries(s.models)
                  .filter(([name]) => name !== 'CFSv2')
                  .map(([name, v]) => ({ name, values: v[mode.key] || [] }))
            : [],
        latest: obs.length ? obs[obs.length - 1] : null,
        latestWeek,
    };
}

/** Share of ensemble members in each phase at one forecast step */
export function memberShares(mode: ModeDef, members: Num[][], step: number): Record<Phase, number> {
    const out: Record<Phase, number> = { pos: 0, neg: 0, neutral: 0 };
    let n = 0;
    for (const m of members) {
        const v = m[step];
        if (v === null || !Number.isFinite(v)) {
            continue;
        }
        out[phaseOf(mode, v)]++;
        n++;
    }
    if (n) {
        out.pos /= n;
        out.neg /= n;
        out.neutral /= n;
    }
    return out;
}

export function quantile(values: number[], q: number): number {
    const v = [...values].sort((a, b) => a - b);
    if (!v.length) {
        return NaN;
    }
    const pos = (v.length - 1) * q;
    const lo = Math.floor(pos);
    const hi = Math.ceil(pos);
    return v[lo] + (v[hi] - v[lo]) * (pos - lo);
}

export function stepValues(members: Num[][], step: number): number[] {
    return members.map(m => m[step]).filter((v): v is number => v !== null && Number.isFinite(v));
}

// ----------------------------------------------------------------------------------------
// Loading
// ----------------------------------------------------------------------------------------

export function getDataUrl(): string {
    try {
        return localStorage.getItem(DATA_URL_STORAGE_KEY) || DEFAULT_DATA_URL;
    } catch {
        return DEFAULT_DATA_URL;
    }
}

export function setDataUrl(url: string | null): void {
    try {
        if (url) {
            localStorage.setItem(DATA_URL_STORAGE_KEY, url);
        } else {
            localStorage.removeItem(DATA_URL_STORAGE_KEY);
        }
    } catch {
        /* storage not available */
    }
}

/** Loads modes.json from the configured URL, falling back to the local dev server. */
export async function loadModesData(): Promise<{ data: ModesData; url: string }> {
    const urls = [getDataUrl()];
    if (!urls.includes(DEV_DATA_URL)) {
        urls.push(DEV_DATA_URL);
    }
    let lastError: unknown = null;
    for (const url of urls) {
        try {
            // bust caches once an hour; the pipeline runs daily
            const bust = Math.floor(Date.now() / 3.6e6);
            const res = await fetch(`${url}${url.includes('?') ? '&' : '?'}h=${bust}`);
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = (await res.json()) as ModesData;
            if (!data?.monthly?.series || !data?.tele) {
                throw new Error('Unexpected data format');
            }
            return { data, url };
        } catch (e) {
            lastError = new Error(`${url}: ${(e as Error).message}`);
        }
    }
    throw lastError || new Error('No data URL configured');
}
