/**
 * Draws the equatorial modes on Windy's main map: the Niño 3.4 box (optionally Niño 1+2,
 * 3 and 4 too), the two poles of the Indian Ocean Dipole and the Atlantic ATL3 box,
 * each filled with its SST anomaly, plus a clickable label with the index and its phase.
 *
 * Leaflet GL (Windy's map) vector layers support neither tooltips nor reliable hover, so
 * all interaction goes through HTML (DivIcon) labels.
 */
import { map } from '@windy/map';

import { MODE_BY_ID, anomalyColor, fmt, formatDay, formatMonth, memberShares, phaseLabel, phaseOf, strengthOf } from './modes';

import type { ModesData, Phase } from './modes';

/** Draw everything at these longitude offsets so wrapped world copies show it too */
const WORLD_COPIES = [-360, 0, 360];

/** (south, north, west, east) in degrees east, as in pipeline/modes_pipeline.py */
const BOXES: Record<string, [number, number, number, number]> = {
    nino34: [-5, 5, 190, 240],
    nino3: [-5, 5, 210, 270],
    nino4: [-5, 5, 160, 210],
    nino12: [-10, 0, 270, 280],
    iod_w: [-10, 10, 50, 70],
    iod_e: [-10, 0, 90, 110],
    atl3: [-3, 3, 340, 360],
};

const BOX_NAMES: Record<string, string> = {
    nino34: 'Niño 3.4',
    nino3: 'Niño 3',
    nino4: 'Niño 4',
    nino12: 'Niño 1+2',
    iod_w: 'IOD west',
    iod_e: 'IOD east',
    atl3: 'ATL3',
};

/** SST anomaly giving the most saturated fill */
const FULL_SCALE = 3;

const PHASE_COLORS: Record<Phase, string> = { pos: '#ff6b4a', neg: '#4aa3ff', neutral: '#d0d6de' };

export type MapSource = 'week' | 'month' | 'forecast';

export interface MapRenderOptions {
    visible: boolean;
    allNino: boolean;
    selected: string | null;
    source: MapSource;
    /** forecast step (CFSv2 lead) when source = 'forecast' */
    step: number;
}

interface Values {
    v: Record<string, number | null>;
    when: string;
    /** member shares per mode id, forecasts only */
    shares: Record<string, { pos: number; neg: number }> | null;
}

const rect = (s: number, n: number, w: number, e: number): L.LatLngExpression[][] => [
    [
        [s, w],
        [n, w],
        [n, e],
        [s, e],
    ],
];

const last = (arr: (number | null)[] | undefined): number | null => {
    if (!arr) {
        return null;
    }
    for (let i = arr.length - 1; i >= 0; i--) {
        if (arr[i] !== null && Number.isFinite(arr[i])) {
            return arr[i];
        }
    }
    return null;
};

export function mapValues(data: ModesData, source: MapSource, step: number): Values | null {
    const keys = [...Object.keys(BOXES), 'dmi'];
    if (source === 'week' && data.daily) {
        const d = data.daily;
        const n = Math.min(7, d.dates.length);
        const v: Record<string, number | null> = {};
        for (const k of keys) {
            const vals = (d.series[k] || []).slice(-n).filter((x): x is number => x !== null);
            v[k] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
        }
        return {
            v,
            when: `7-day mean to ${formatDay(d.dates[d.dates.length - 1])} (OISST)`,
            shares: null,
        };
    }
    if (source === 'forecast' && data.seasonal) {
        const s = data.seasonal;
        const i = Math.min(step, s.months.length - 1);
        const v: Record<string, number | null> = {};
        for (const k of keys) {
            v[k] = s.mean[k] ? s.mean[k][i] : null;
        }
        const shares: Record<string, { pos: number; neg: number }> = {};
        for (const id of ['enso', 'iod', 'atl']) {
            const mode = MODE_BY_ID[id];
            const sh = memberShares(mode, s.members[mode.key] || [], i);
            shares[id] = { pos: sh.pos, neg: sh.neg };
        }
        return { v, when: `${formatMonth(s.months[i])} · ${s.model} ensemble mean`, shares };
    }
    const m = data.monthly;
    const v: Record<string, number | null> = {};
    for (const k of keys) {
        v[k] = last(m.series[k]);
    }
    return { v, when: `${formatMonth(m.months[m.months.length - 1])} (ERSSTv5)`, shares: null };
}

export class ModesMapLayer {
    private group: L.LayerGroup;
    private onSelect: (id: string) => void;

    constructor(onSelect: (id: string) => void) {
        this.onSelect = onSelect;
        this.group = new L.LayerGroup([]);
        this.group.addTo(map);
    }

    destroy(): void {
        this.group.clearLayers();
        this.group.remove();
    }

    render(data: ModesData | null, opts: MapRenderOptions): void {
        try {
            this.group.clearLayers();
            if (data && opts.visible) {
                this.draw(data, opts);
            }
        } catch (e) {
            // a drawing problem must never break the plugin pane
            console.error('windy-plugin-climate-modes: map overlay failed', e);
        }
    }

    private add(layer: L.Layer): void {
        this.group.addLayer(layer);
    }

    private draw(data: ModesData, opts: MapRenderOptions): void {
        const vals = mapValues(data, opts.source, opts.step);
        if (!vals) {
            return;
        }
        const { v } = vals;
        const boxKeys = opts.allNino
            ? ['nino4', 'nino3', 'nino12', 'nino34', 'iod_w', 'iod_e', 'atl3']
            : ['nino34', 'iod_w', 'iod_e', 'atl3'];
        const modeOfBox = (k: string) => (k.startsWith('nino') ? 'enso' : k.startsWith('iod') ? 'iod' : 'atl');

        for (const offset of WORLD_COPIES) {
            for (const k of boxKeys) {
                const [s, n, w, e] = BOXES[k];
                const isMain = k === 'nino34' || !k.startsWith('nino');
                const sel = opts.selected === modeOfBox(k);
                this.add(
                    new L.Polygon(rect(s, n, w + offset, e + offset), {
                        color: '#ffffff',
                        opacity: sel ? 1 : 0.75,
                        weight: sel ? 2.5 : isMain ? 1.5 : 1,
                        dashArray: isMain ? undefined : '4 4',
                        fill: true,
                        fillColor: anomalyColor(v[k], FULL_SCALE),
                        fillOpacity: isMain ? 0.55 : 0.3,
                        interactive: false,
                    }),
                );
                if (!isMain) {
                    // small value tag inside the extra Niño boxes
                    this.label([n - 1.2, (w + e) / 2 + offset], `<div class="cm-tag">${BOX_NAMES[k]} ${fmt(v[k], 1)}</div>`, 90, 16, null);
                }
            }

            // IOD: poles + dipole label
            this.add(
                new L.Polyline(
                    [
                        [0, 60 + offset],
                        [-5, 100 + offset],
                    ],
                    { color: '#ffffff', opacity: 0.6, weight: 1, dashArray: '2 4', interactive: false },
                ),
            );
            // labels over open ocean: ENSO north of its box, IOD / ATL3 south of theirs
            this.modeLabel(
                [-12, 80 + offset],
                'iod',
                v.dmi,
                `W ${fmt(v.iod_w, 1)} · E ${fmt(v.iod_e, 1)}`,
                vals,
                opts.selected === 'iod',
                false,
            );
            this.modeLabel([11, 215 + offset], 'enso', v.nino34, 'Niño 3.4', vals, opts.selected === 'enso', true);
            this.modeLabel([-5, 350 + offset], 'atl', v.atl3, 'ATL3', vals, opts.selected === 'atl', false);
        }
    }

    private modeLabel(
        at: [number, number],
        id: string,
        value: number | null,
        sub: string,
        vals: Values,
        selected: boolean,
        above: boolean,
    ): void {
        const mode = MODE_BY_ID[id];
        const phase = phaseOf(mode, value);
        const strength = strengthOf(mode, value);
        const share = vals.shares?.[id];
        const html =
            `<div class="cm-label cm-label--${phase}${selected ? ' cm-label--sel' : ''}" ` +
            `style="border-color:${PHASE_COLORS[phase]}">` +
            `<b>${mode.short}</b> <span class="cm-val" style="color:${PHASE_COLORS[phase]}">${fmt(value)} ${mode.unit}</span>` +
            `<small>${phaseLabel(mode, value)}${strength ? ` (${strength})` : ''} · ${sub}</small>` +
            (share
                ? `<small>${Math.round(share.pos * 100)}% ${mode.pos} · ${Math.round(share.neg * 100)}% ${mode.neg}</small>`
                : '') +
            `</div>`;
        this.label(at, html, 190, share ? 54 : 40, () => this.onSelect(id), above);
    }

    private label(
        at: [number, number],
        html: string,
        w: number,
        h: number,
        onClick: (() => void) | null,
        above = true,
    ): void {
        const marker = new L.Marker(at, {
            icon: new L.DivIcon({
                className: 'cm-label-icon',
                html,
                iconSize: [w, h],
                iconAnchor: [w / 2, above ? h : 0],
            }),
            interactive: !!onClick,
        });
        if (onClick) {
            marker.on('click', onClick);
        }
        this.add(marker);
    }
}
