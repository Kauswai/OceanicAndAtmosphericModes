<div class="chart" bind:this={wrapper}>
    <svg
        viewBox="0 0 {VW} {VH}"
        on:pointermove={onMove}
        on:pointerleave={() => (hover = null)}
        on:click={onClick}
        role="img"
        aria-label="{series.mode.name} chart"
    >
        <defs>
            <clipPath id="{uid}-plot">
                <rect x={ML} y={MT} width={VW - ML - MR} height={VH - MT - MB} />
            </clipPath>
            <clipPath id="{uid}-above">
                <rect x={ML} y={MT} width={VW - ML - MR} height={Math.max(0, y(0) - MT)} />
            </clipPath>
            <clipPath id="{uid}-below">
                <rect x={ML} y={y(0)} width={VW - ML - MR} height={Math.max(0, VH - MB - y(0))} />
            </clipPath>
        </defs>

        <rect class="bg" x={ML} y={MT} width={VW - ML - MR} height={VH - MT - MB} />
        {#if fc && fcStart < x1}
            <rect class="fc-bg" x={x(fcStart)} y={MT} width={Math.max(0, VW - MR - x(fcStart))} height={VH - MT - MB} />
            <text class="fc-label" x={x(fcStart) + 4} y={MT + 11}>{fc.model} forecast</text>
        {/if}

        <g clip-path="url(#{uid}-plot)">
            <!-- neutral band and phase lines -->
            <rect
                class="neutral"
                x={ML}
                y={y(series.mode.threshold)}
                width={VW - ML - MR}
                height={Math.max(0, y(-series.mode.threshold) - y(series.mode.threshold))}
            />
            {#each [series.mode.threshold, ...series.mode.levels] as lv}
                <line class="lvl lvl--pos" x1={ML} x2={VW - MR} y1={y(lv)} y2={y(lv)} />
                <line class="lvl lvl--neg" x1={ML} x2={VW - MR} y1={y(-lv)} y2={y(-lv)} />
            {/each}
            <line class="zero" x1={ML} x2={VW - MR} y1={y(0)} y2={y(0)} />

            <!-- observed record, filled red above / blue below zero -->
            {#if obsArea}
                <path class="fill-pos" d={obsArea} clip-path="url(#{uid}-above)" />
                <path class="fill-neg" d={obsArea} clip-path="url(#{uid}-below)" />
            {/if}
            {#if showDaily && dailyVisible.length > 1}
                <polyline class="daily" points={pts(dailyVisible)} />
            {/if}
            {#if showOfficial && officialVisible.length > 1}
                <polyline class="official" points={pts(officialVisible)} />
            {/if}

            <!-- ensemble -->
            {#if fc}
                {#if showSpread && spreadPath}
                    <path class="spread" d={spreadPath} />
                {/if}
                {#if showMembers}
                    {#each memberLines as line}
                        <polyline class="member" points={line} />
                    {/each}
                {/if}
                {#if showModels}
                    {#each modelLines as ml, i}
                        <polyline class="model" style:stroke={MODEL_COLORS[i % MODEL_COLORS.length]} points={ml.line} />
                    {/each}
                {/if}
            {/if}

            {#if obsVisible.length > 1}
                <polyline class="obs" points={pts(obsVisible)} />
            {/if}
            {#if series.mode.freq === 'monthly'}
                {#each obsVisible as p}
                    <circle class="obs-dot" cx={x(p.t)} cy={y(p.v)} r="2.2" />
                {/each}
            {/if}

            {#if fc && showMean && meanLine}
                <polyline class="mean" points={meanLine} />
                {#each fcPoints as p, i}
                    {#if p}
                        <circle
                            class="mean-dot"
                            class:mean-dot--sel={i === selectedStep}
                            cx={x(p.t)}
                            cy={y(p.v)}
                            r={i === selectedStep ? 4.5 : 2.8}
                        />
                    {/if}
                {/each}
            {/if}

            <!-- latest observation, Windy timeline, selection -->
            {#if series.latest}
                <line class="now" x1={x(series.latest.t)} x2={x(series.latest.t)} y1={MT} y2={VH - MB} />
            {/if}
            {#if markerTime !== null && markerTime >= x0 && markerTime <= x1}
                <line class="marker" x1={x(markerTime)} x2={x(markerTime)} y1={MT} y2={VH - MB} />
            {/if}
            {#if fc && selectedStep !== null && fc.times[selectedStep] !== undefined}
                <line class="sel" x1={x(fc.times[selectedStep])} x2={x(fc.times[selectedStep])} y1={MT} y2={VH - MB} />
            {/if}
            {#if hover}
                <line class="cross" x1={x(hover.t)} x2={x(hover.t)} y1={MT} y2={VH - MB} />
            {/if}
        </g>

        <!-- axes -->
        {#each yTicks as v}
            <text class="ytick" x={ML - 4} y={y(v) + 3}>{v === 0 ? '0' : v.toFixed(yDigits)}</text>
        {/each}
        {#each xTicks as tk}
            <line class="xgrid" x1={x(tk.t)} x2={x(tk.t)} y1={VH - MB} y2={VH - MB + 3} />
            <text class="xtick" x={x(tk.t)} y={VH - MB + 13}>{tk.label}</text>
        {/each}
        <text class="unit" x="2" y={MT + 3}>{series.mode.unit}</text>
        <text class="phase-tag phase-tag--pos" x={ML + 4} y={MT + 11}>{series.mode.pos}</text>
        <text class="phase-tag phase-tag--neg" x={ML + 4} y={VH - MB - 5}>{series.mode.neg}</text>
    </svg>

    {#if hover}
        <div class="tip" style:left="{hover.left}px" style:top="{hover.top}px">
            {@html hover.html}
        </div>
    {/if}
</div>

<script lang="ts" context="module">
    let counter = 0;
</script>

<script lang="ts">
    import { createEventDispatcher } from 'svelte';

    import {
        fmt,
        formatDay,
        formatMonth,
        memberShares,
        phaseLabel,
        quantile,
        stepValues,
    } from './modes';

    import type { ModeSeries, Point } from './modes';

    export let series: ModeSeries;
    /** history shown before the latest observation, in days */
    export let historyDays = 730;
    export let showMembers = true;
    export let showSpread = true;
    export let showMean = true;
    export let showModels = true;
    export let showOfficial = false;
    export let showDaily = true;
    export let markerTime: number | null = null;
    export let selectedStep: number | null = null;

    const dispatch = createEventDispatcher<{ select: number }>();
    const uid = `cm-chart-${++counter}`;
    const VW = 440;
    const VH = 240;
    const ML = 34;
    const MR = 8;
    const MT = 8;
    const MB = 22;
    const DAY = 86400000;
    const MODEL_COLORS = ['#c792ea', '#7fdbca', '#f78c6c', '#82aaff', '#c3e88d', '#ffcb6b', '#ff5370'];

    let wrapper: HTMLDivElement;
    let hover: { t: number; left: number; top: number; html: string } | null = null;

    $: fc = series.forecast;
    $: monthly = series.mode.freq === 'monthly';
    $: lastObsT = series.latest ? series.latest.t : Date.now();
    $: fcEnd = fc && fc.times.length ? fc.times[fc.times.length - 1] : lastObsT;
    $: fcStart = fc && fc.times.length ? Math.min(fc.times[0], lastObsT + (monthly ? 15 : 0.5) * DAY) : lastObsT;
    $: x0 = lastObsT - historyDays * DAY;
    $: x1 = Math.max(lastObsT, fcEnd) + (monthly ? 12 : 0.6) * DAY;

    $: obsVisible = series.obs.filter(p => p.t >= x0 - 40 * DAY);
    $: dailyVisible = series.obsDaily.filter(p => p.t >= x0);
    $: officialVisible = series.official ? series.official.points.filter(p => p.t >= x0 - 40 * DAY) : [];

    /** mean track points, starting from the latest observation */
    $: fcPoints = fc
        ? fc.mean.map((v, i) => (v === null ? null : { t: fc!.times[i], label: fc!.labels[i], v }))
        : [];
    $: anchor = series.latest;

    // ---- y domain from everything visible
    $: yDomain = computeDomain(series, obsVisible, showDaily ? dailyVisible : [], showMembers || showSpread);
    function computeDomain(s: ModeSeries, obs: Point[], daily: Point[], withMembers: boolean): [number, number] {
        const vals: number[] = [s.mode.threshold, -s.mode.threshold];
        obs.forEach(p => vals.push(p.v));
        daily.forEach(p => vals.push(p.v));
        if (s.forecast) {
            const all: number[] = [];
            s.forecast.members.forEach(m => m.forEach(v => v !== null && Number.isFinite(v) && all.push(v)));
            if (withMembers && all.length) {
                // ignore the most extreme 1 % so a single outlier does not squash the plot
                vals.push(quantile(all, 0.005), quantile(all, 0.995));
            }
            s.forecast.mean.forEach(v => v !== null && vals.push(v));
        }
        let lo = Math.min(...vals);
        let hi = Math.max(...vals);
        const pad = (hi - lo) * 0.08 || 0.5;
        lo -= pad;
        hi += pad;
        return [lo, hi];
    }

    $: x = (t: number) => ML + ((t - x0) / (x1 - x0)) * (VW - ML - MR);
    $: y = (v: number) => MT + ((yDomain[1] - v) / (yDomain[1] - yDomain[0])) * (VH - MT - MB);
    $: pts = (p: Point[]) => p.map(q => `${x(q.t).toFixed(1)},${y(q.v).toFixed(1)}`).join(' ');

    $: obsArea = buildArea(obsVisible, x, y);
    function buildArea(p: Point[], fx: typeof x, fy: typeof y): string | null {
        if (p.length < 2) {
            return null;
        }
        const z = fy(0);
        return (
            `M${fx(p[0].t)},${z}` +
            p.map(q => `L${fx(q.t).toFixed(1)},${fy(q.v).toFixed(1)}`).join('') +
            `L${fx(p[p.length - 1].t)},${z}Z`
        );
    }

    $: memberLines = fc ? fc.members.map(m => lineFrom(m, x, y)) : [];
    $: meanLine = fc ? lineFrom(fc.mean, x, y) : '';
    $: modelLines = fc
        ? series.models.filter(m => m.values.some(v => v !== null)).map(m => ({ name: m.name, line: lineFrom(m.values, x, y) }))
        : [];

    /** polyline from the latest observation through the forecast steps */
    function lineFrom(values: (number | null)[], fx: typeof x, fy: typeof y): string {
        const out: string[] = [];
        if (anchor && fc && anchor.t < fc.times[0]) {
            out.push(`${fx(anchor.t).toFixed(1)},${fy(anchor.v).toFixed(1)}`);
        }
        values.forEach((v, i) => {
            if (v !== null && Number.isFinite(v)) {
                out.push(`${fx(fc!.times[i]).toFixed(1)},${fy(v).toFixed(1)}`);
            }
        });
        return out.join(' ');
    }

    $: spreadPath = fc ? buildSpread(x, y) : null;
    function buildSpread(fx: typeof x, fy: typeof y): string | null {
        if (!fc) {
            return null;
        }
        const top: string[] = [];
        const bot: string[] = [];
        if (anchor && anchor.t < fc.times[0]) {
            top.push(`${fx(anchor.t)},${fy(anchor.v)}`);
            bot.push(`${fx(anchor.t)},${fy(anchor.v)}`);
        }
        fc.times.forEach((t, i) => {
            const v = stepValues(fc!.members, i);
            if (v.length) {
                top.push(`${fx(t).toFixed(1)},${fy(quantile(v, 0.9)).toFixed(1)}`);
                bot.push(`${fx(t).toFixed(1)},${fy(quantile(v, 0.1)).toFixed(1)}`);
            }
        });
        if (top.length < 2) {
            return null;
        }
        return `M${top.join('L')}L${bot.reverse().join('L')}Z`;
    }

    // ---- ticks
    $: yDigits = yDomain[1] - yDomain[0] < 1.2 ? 2 : yDomain[1] - yDomain[0] < 6 ? 1 : 0;
    $: yTicks = niceTicks(yDomain[0], yDomain[1], 6);
    function niceTicks(lo: number, hi: number, n: number): number[] {
        const span = hi - lo;
        const raw = span / n;
        const mag = Math.pow(10, Math.floor(Math.log10(raw)));
        const step = [1, 2, 2.5, 5, 10].map(s => s * mag).find(s => span / s <= n) || 10 * mag;
        const out = [];
        for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) {
            out.push(Math.round(v / step) * step);
        }
        return out;
    }

    $: xTicks = buildXTicks(x0, x1, monthly, (x1 - x0) / DAY);
    function buildXTicks(a: number, b: number, isMonthly: boolean, span: number) {
        const out: { t: number; label: string }[] = [];
        if (isMonthly) {
            const every = span > 1500 ? 12 : span > 700 ? 6 : 3;
            const d = new Date(a);
            let yy = d.getUTCFullYear();
            let mm = d.getUTCMonth() + 1;
            for (let k = 0; k < 200; k++) {
                const t = Date.UTC(yy, mm - 1, 1);
                if (t > b) {
                    break;
                }
                if (t >= a && (mm - 1) % every === 0) {
                    out.push({
                        t,
                        label:
                            mm === 1 || every === 12
                                ? `${yy}`
                                : new Date(t).toLocaleDateString(undefined, { month: 'short', timeZone: 'UTC' }),
                    });
                }
                mm++;
                if (mm > 12) {
                    mm = 1;
                    yy++;
                }
            }
        } else {
            const total = (b - a) / DAY;
            const every = total > 100 ? 21 : total > 45 ? 14 : 7;
            // anchor ticks on Mondays-ish fixed epoch so they don't jump around
            const first = Math.ceil(a / DAY / every) * every * DAY;
            for (let t = first; t <= b; t += every * DAY) {
                out.push({ t, label: formatDay(new Date(t).toISOString()) });
            }
        }
        return out;
    }

    // ---- hover & click
    function nearestStep(t: number): number | null {
        if (!fc) {
            return null;
        }
        let best: number | null = null;
        let bd = Infinity;
        fc.times.forEach((ft, i) => {
            const d = Math.abs(ft - t);
            if (d < bd) {
                bd = d;
                best = i;
            }
        });
        const half = (monthly ? 16 : 0.6) * DAY;
        return bd <= half ? best : null;
    }

    function nearest(p: Point[], t: number, maxDays: number): Point | null {
        let best: Point | null = null;
        let bd = Infinity;
        for (const q of p) {
            const d = Math.abs(q.t - t);
            if (d < bd) {
                bd = d;
                best = q;
            }
        }
        return bd <= maxDays * DAY ? best : null;
    }

    function svgTime(e: PointerEvent | MouseEvent): number {
        const box = wrapper.getBoundingClientRect();
        const sx = ((e.clientX - box.left) / box.width) * VW;
        return x0 + ((sx - ML) / (VW - ML - MR)) * (x1 - x0);
    }

    function onMove(e: PointerEvent) {
        const t = svgTime(e);
        if (t < x0 || t > x1) {
            hover = null;
            return;
        }
        const m = series.mode;
        const lines: string[] = [];
        let ht = t;
        const step = nearestStep(t);
        if (step !== null && fc && (!series.latest || fc.times[step] > series.latest.t - DAY)) {
            ht = fc.times[step];
            const vals = stepValues(fc.members, step);
            const mean = fc.mean[step];
            const sh = memberShares(m, fc.members, step);
            lines.push(
                `<b>${monthly ? formatMonth(fc.labels[step]) : formatDay(fc.labels[step])}</b> · ${fc.model} ` +
                    (monthly ? `lead ${step}` : `day +${step}`),
            );
            lines.push(`Ensemble mean <b>${fmt(mean)}</b> ${m.unit} · ${phaseLabel(m, mean)}`);
            if (vals.length) {
                lines.push(
                    `10–90 %: ${fmt(quantile(vals, 0.1))} … ${fmt(quantile(vals, 0.9))} ` +
                        `<small>(range ${fmt(Math.min(...vals))} … ${fmt(Math.max(...vals))})</small>`,
                );
                lines.push(
                    `<span class="p">${Math.round(sh.pos * 100)}% ${m.pos}</span> · ` +
                        `<span class="n">${Math.round(sh.neg * 100)}% ${m.neg}</span>`,
                );
            }
            if (showModels && series.models.length) {
                const mm = series.models
                    .filter(md => md.values[step] !== null && md.values[step] !== undefined)
                    .map(md => `${md.name} ${fmt(md.values[step])}`);
                if (mm.length) {
                    lines.push(`<small>${mm.join(' · ')}</small>`);
                }
            }
        } else {
            const o = nearest(series.obs, t, monthly ? 16 : 1);
            if (o) {
                ht = o.t;
                lines.push(
                    `<b>${monthly ? formatMonth(o.label) : formatDay(o.label)}</b> · observed`,
                    `${m.short} <b>${fmt(o.v)}</b> ${m.unit} · ${phaseLabel(m, o.v)}`,
                );
                if (series.official && showOfficial) {
                    const of = nearest(series.official.points, o.t, 2);
                    if (of) {
                        lines.push(`${series.official.name}: ${fmt(of.v)}`);
                    }
                }
            }
            if (showDaily && series.obsDaily.length) {
                const d = nearest(series.obsDaily, t, 1);
                if (d) {
                    if (!o) {
                        ht = d.t;
                    }
                    lines.push(`<small>Daily OISST ${formatDay(d.label)}: ${fmt(d.v)}</small>`);
                }
            }
        }
        if (!lines.length) {
            hover = null;
            return;
        }
        const box = wrapper.getBoundingClientRect();
        const px = e.clientX - box.left;
        const left = px > box.width / 2 ? Math.max(0, px - 214) : px + 14;
        hover = { t: ht, left, top: 4, html: lines.join('<br>') };
    }

    function onClick(e: MouseEvent) {
        const step = nearestStep(svgTime(e));
        if (step !== null) {
            dispatch('select', step);
        }
    }
</script>

<style lang="less">
    .chart {
        position: relative;
        width: 100%;
        user-select: none;
    }
    svg {
        display: block;
        width: 100%;
        height: auto;
        cursor: crosshair;
        touch-action: pan-y;
    }
    .bg {
        fill: #10151c;
    }
    .fc-bg {
        fill: rgba(255, 209, 102, 0.06);
    }
    .fc-label {
        fill: rgba(255, 209, 102, 0.7);
        font-size: 9px;
    }
    .neutral {
        fill: rgba(255, 255, 255, 0.05);
    }
    .lvl {
        stroke-width: 0.8;
        stroke-dasharray: 3 4;
        &--pos {
            stroke: rgba(255, 107, 74, 0.45);
        }
        &--neg {
            stroke: rgba(74, 163, 255, 0.45);
        }
    }
    .zero {
        stroke: rgba(255, 255, 255, 0.4);
        stroke-width: 0.8;
    }
    .fill-pos {
        fill: rgba(255, 107, 74, 0.45);
    }
    .fill-neg {
        fill: rgba(74, 163, 255, 0.45);
    }
    .obs {
        fill: none;
        stroke: #fff;
        stroke-width: 1.6;
        stroke-linejoin: round;
    }
    .obs-dot {
        fill: #fff;
    }
    .daily {
        fill: none;
        stroke: #9ad7ff;
        stroke-width: 0.9;
        opacity: 0.8;
    }
    .official {
        fill: none;
        stroke: #b9c4d0;
        stroke-width: 1.3;
        stroke-dasharray: 4 3;
    }
    .member {
        fill: none;
        stroke: #ff9f43;
        stroke-width: 0.8;
        opacity: 0.35;
    }
    .spread {
        fill: rgba(255, 159, 67, 0.18);
        stroke: none;
    }
    .model {
        fill: none;
        stroke-width: 1.2;
        stroke-dasharray: 5 3;
        opacity: 0.85;
    }
    .mean {
        fill: none;
        stroke: #ffd166;
        stroke-width: 2.5;
        stroke-linejoin: round;
    }
    .mean-dot {
        fill: #ffd166;
        stroke: #10151c;
        stroke-width: 0.8;
        &--sel {
            stroke: #fff;
            stroke-width: 1.5;
        }
    }
    .now {
        stroke: rgba(255, 255, 255, 0.5);
        stroke-width: 1;
        stroke-dasharray: 2 2;
    }
    .marker {
        stroke: #36e0ff;
        stroke-width: 1.2;
    }
    .sel {
        stroke: #ffd166;
        stroke-width: 1;
        stroke-dasharray: 3 2;
    }
    .cross {
        stroke: rgba(255, 255, 255, 0.35);
        stroke-width: 1;
    }
    .ytick {
        fill: rgba(255, 255, 255, 0.55);
        font-size: 9px;
        text-anchor: end;
    }
    .xtick {
        fill: rgba(255, 255, 255, 0.55);
        font-size: 9px;
        text-anchor: middle;
    }
    .xgrid {
        stroke: rgba(255, 255, 255, 0.3);
    }
    .unit {
        fill: rgba(255, 255, 255, 0.4);
        font-size: 8px;
    }
    .phase-tag {
        font-size: 9px;
        text-anchor: start;
        opacity: 0.7;
        &--pos {
            fill: #ff8a70;
        }
        &--neg {
            fill: #7fbfff;
        }
    }
    .tip {
        position: absolute;
        z-index: 3;
        width: 200px;
        padding: 6px 8px;
        border-radius: 4px;
        background: rgba(0, 0, 0, 0.9);
        color: #fff;
        font-size: 11px;
        line-height: 1.45;
        pointer-events: none;
        :global(small) {
            opacity: 0.7;
        }
        :global(.p) {
            color: #ff8a70;
        }
        :global(.n) {
            color: #7fbfff;
        }
    }
</style>
