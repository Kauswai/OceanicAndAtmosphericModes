<div class="plugin__mobile-header">
    {title}
</div>
<section class="plugin__content cm">
    <div
        class="plugin__title plugin__title--chevron-back"
        on:click={() => bcast.emit('rqstOpen', 'menu')}
    >
        {title}
    </div>

    {#if loading}
        <div class="cm-msg">Loading climate indices…</div>
    {:else if error}
        <div class="cm-msg cm-msg--error">
            Could not load the data.<br />
            <small>{error}</small>
        </div>
    {/if}

    {#if data}
        <div class="tabs">
            <button class="tabs__btn" class:tabs__btn--on={tab === 'equatorial'} on:click={() => setTab('equatorial')}>
                Equatorial modes
            </button>
            <button class="tabs__btn" class:tabs__btn--on={tab === 'oscillation'} on:click={() => setTab('oscillation')}>
                Oscillations
            </button>
        </div>

        {#if tab === 'equatorial'}
            <div class="cards">
                {#each equatorial as s (s.mode.id)}
                    {@const cur = s.latestWeek || s.latest}
                    {@const ph = phaseOf(s.mode, cur ? cur.v : null)}
                    <button
                        class="card card--{ph}"
                        class:card--sel={selectedId === s.mode.id}
                        on:click={() => select(s.mode.id)}
                        title="Show the {s.mode.short} graph"
                    >
                        <div class="card__name">{s.mode.short}</div>
                        <div class="card__val">{fmt(cur ? cur.v : null)}<small>{s.mode.unit}</small></div>
                        <div class="card__phase">
                            {phaseLabel(s.mode, cur ? cur.v : null)}
                            {#if strengthOf(s.mode, cur ? cur.v : null)}
                                <span>({strengthOf(s.mode, cur ? cur.v : null)})</span>
                            {/if}
                        </div>
                        <div class="card__sub">
                            {#if s.latest}{formatMonth(s.latest.label)} {fmt(s.latest.v)}{/if}
                            {#if trend(s)}<br />{trend(s)}{/if}
                        </div>
                    </button>
                {/each}
            </div>

            <div class="mapopts size-s">
                <label><input type="checkbox" bind:checked={mapVisible} /> On map</label>
                <select bind:value={mapSource} disabled={!mapVisible}>
                    <option value="week" disabled={!data.daily}>Latest week (daily OISST)</option>
                    <option value="month">Latest month (ERSSTv5)</option>
                    <option value="forecast" disabled={!data.seasonal}>Forecast month (CFSv2 mean)</option>
                </select>
                {#if mapSource === 'forecast' && data.seasonal}
                    <select bind:value={mapStep} disabled={!mapVisible}>
                        {#each data.seasonal.months as m, i}
                            <option value={i}>{formatMonth(m)}</option>
                        {/each}
                    </select>
                {/if}
                <label><input type="checkbox" bind:checked={allNino} disabled={!mapVisible} /> Niño 1+2 / 3 / 4</label>
                <button class="linkbtn" on:click={showSstLayer} title="Switch Windy's layer to sea temperature">SST layer</button>
            </div>
            {#if mapVisible && mapInfo}
                <div class="mapinfo size-xs">Map: {mapInfo.when}. Click a label on the map to open its graph.</div>
            {/if}
        {:else}
            <div class="grid">
                {#each oscillations as s (s.mode.id)}
                    {@const cur = s.latest}
                    {@const ph = phaseOf(s.mode, cur ? cur.v : null)}
                    <button
                        class="osc osc--{ph}"
                        class:osc--sel={selectedId === s.mode.id}
                        class:osc--na={!cur}
                        on:click={() => select(s.mode.id)}
                        title={s.mode.name}
                    >
                        <div class="osc__name">{s.mode.short}</div>
                        <div class="osc__val">{fmt(cur ? cur.v : null, s.mode.id === 'pmm' ? 1 : 2)}</div>
                        <div class="osc__trend">{trend(s, true) || ' '}</div>
                    </button>
                {/each}
            </div>
        {/if}

        <!-- graph of the selected mode -->
        {#if selected}
            {@const s = selected}
            {@const m = s.mode}
            <div class="detail">
                <div class="detail__head">
                    <div>
                        <div class="size-l">{m.name}</div>
                        <div class="size-xs muted">
                            {#if s.latest}
                                Observed {m.freq === 'monthly' ? formatMonth(s.latest.label) : formatDay(s.latest.label)}:
                                <b>{fmt(s.latest.v)} {m.unit}</b> · {phaseLabel(m, s.latest.v)}
                            {/if}
                            {#if s.latestWeek}
                                · last 7 days {fmt(s.latestWeek.v)}
                            {/if}
                        </div>
                    </div>
                    <button class="detail__close" on:click={() => (selectedId = null)} title="Close graph">×</button>
                </div>

                <div class="hist size-xs">
                    History
                    {#each historyChoices(m) as hc}
                        <button
                            class="chip"
                            class:chip--on={historyFor(m) === hc.days}
                            on:click={() => setHistory(m, hc.days)}>{hc.label}</button
                        >
                    {/each}
                </div>

                <Chart
                    series={s}
                    historyDays={historyFor(m)}
                    {showMembers}
                    {showSpread}
                    {showMean}
                    showModels={showModels && m.freq === 'monthly'}
                    showOfficial={showOfficial && !!s.official}
                    showDaily={showDaily && s.obsDaily.length > 0}
                    markerTime={m.freq === 'daily' && syncTimeline ? timestamp : null}
                    selectedStep={step}
                    on:select={e => selectStep(e.detail)}
                />

                {#if s.forecast && step !== null && s.forecast.labels[step]}
                    {@const fc = s.forecast}
                    {@const sh = memberShares(m, fc.members, step)}
                    <div class="probs">
                        <div class="probs__title size-xs">
                            {m.freq === 'monthly' ? formatMonth(fc.labels[step]) : formatDay(fc.labels[step])}
                            ({m.freq === 'monthly' ? `lead ${step}` : `day +${step}`}) · {fc.members.length}
                            {fc.model} members · mean <b>{fmt(fc.mean[step])}</b>
                        </div>
                        <div class="probs__bar">
                            <div class="probs__neg" style:width="{sh.neg * 100}%">
                                {#if sh.neg >= 0.12}{Math.round(sh.neg * 100)}%{/if}
                            </div>
                            <div class="probs__neu" style:width="{sh.neutral * 100}%">
                                {#if sh.neutral >= 0.12}{Math.round(sh.neutral * 100)}%{/if}
                            </div>
                            <div class="probs__pos" style:width="{sh.pos * 100}%">
                                {#if sh.pos >= 0.12}{Math.round(sh.pos * 100)}%{/if}
                            </div>
                        </div>
                        <div class="probs__legend size-xxs">
                            <span class="n">{m.neg}</span><span>{m.neutral}</span><span class="p">{m.pos}</span>
                        </div>
                        <div class="steps">
                            <button class="day__btn" on:click={() => selectStep((step ?? 0) - 1)} disabled={step <= 0}>‹</button>
                            <input
                                type="range"
                                min="0"
                                max={fc.labels.length - 1}
                                value={step}
                                on:input={e => selectStep(+e.currentTarget.value)}
                            />
                            <button
                                class="day__btn"
                                on:click={() => selectStep((step ?? 0) + 1)}
                                disabled={step >= fc.labels.length - 1}>›</button
                            >
                        </div>
                    </div>
                {/if}

                <div class="opts size-s">
                    <label><input type="checkbox" bind:checked={showMean} /> Ensemble mean</label>
                    <label><input type="checkbox" bind:checked={showMembers} /> Members</label>
                    <label><input type="checkbox" bind:checked={showSpread} /> 10–90 % spread</label>
                    {#if m.freq === 'monthly'}
                        <label><input type="checkbox" bind:checked={showModels} disabled={!s.models.length} /> NMME models</label>
                    {/if}
                    {#if s.obsDaily.length}
                        <label><input type="checkbox" bind:checked={showDaily} /> Daily OISST</label>
                    {/if}
                    {#if s.official}
                        <label><input type="checkbox" bind:checked={showOfficial} /> {OFFICIAL_LABELS[m.official || ''] || 'Official'}</label>
                    {/if}
                    {#if m.freq === 'daily'}
                        <label><input type="checkbox" bind:checked={syncTimeline} /> Windy timeline</label>
                    {/if}
                </div>

                <div class="legend size-xs">
                    <span><i style:background="#fff" /> observed{m.freq === 'monthly' ? ' (monthly)' : ''}</span>
                    {#if s.obsDaily.length && showDaily}<span><i style:background="#9ad7ff" /> daily</span>{/if}
                    <span><i style:background="#ffd166" /> ensemble mean</span>
                    <span><i style:background="#ff9f43" style:opacity="0.6" /> members / spread</span>
                    {#if m.freq === 'monthly' && showModels}
                        {#each s.models.filter(md => md.values.some(v => v !== null)) as md, i}
                            <span><i class="dash" style:border-color={MODEL_COLORS[i % MODEL_COLORS.length]} /> {md.name}</span>
                        {/each}
                    {/if}
                    {#if m.freq === 'daily' && syncTimeline}<span><i style:background="#36e0ff" /> Windy time</span>{/if}
                </div>

                <div class="desc size-xs">{m.description}</div>

                <div class="foot size-xxs">
                    Observed: {s.obsSource}{#if s.obsDaily.length}; daily: {data.daily?.source}{/if}.
                    {#if s.forecast}
                        Forecast: {s.forecast.model}, {s.forecast.members.length} members, init
                        {s.forecast.init.replace('T', ' ')} ({s.forecast.source}).
                    {/if}
                    {#if m.id === 'aam'}
                        AAM computed from GEFS zonal wind on 12 levels; anomaly vs NCEP/NCAR R1 1991–2020.
                    {/if}
                    {#if validationNote(m.id)}{validationNote(m.id)}{/if}
                    Click the chart to pick a forecast {m.freq === 'monthly' ? 'month' : 'day'}.
                </div>
            </div>
        {:else}
            <div class="hint size-s">
                Click a {tab === 'equatorial' ? 'mode' : 'button'} to show its graph with the observed record and
                the {tab === 'equatorial' ? 'CFSv2 seasonal' : 'GEFS / CFSv2'} ensemble forecast.
            </div>
        {/if}

        <div class="foot size-xxs">Data updated {data.generated.replace('T', ' ')}</div>
    {/if}

    <details class="settings size-xs">
        <summary>Data source</summary>
        <input type="text" bind:value={urlInput} placeholder="https://…/modes.json" />
        <div class="settings__row">
            <button class="button button--variant-orange size-xs" on:click={saveUrl}>Save &amp; reload</button>
            <button class="button size-xs" on:click={resetUrl}>Default</button>
        </div>
        {#if loadedFrom}<div class="muted">Loaded from {loadedFrom}</div>{/if}
    </details>
</section>

<script lang="ts">
    import bcast from '@windy/broadcast';
    import store from '@windy/store';
    import { onDestroy, onMount } from 'svelte';

    import Chart from './Chart.svelte';
    import { ModesMapLayer, mapValues } from './mapLayer';
    import {
        MODES,
        MODE_BY_ID,
        dayTimestamp,
        fmt,
        formatDay,
        formatMonth,
        getDataUrl,
        isoDay,
        loadModesData,
        memberShares,
        phaseLabel,
        phaseOf,
        seriesFor,
        setDataUrl,
        strengthOf,
    } from './modes';
    import config from './pluginConfig';

    import type { MapSource } from './mapLayer';
    import type { Group, ModeDef, ModeSeries, ModesData } from './modes';

    const { title } = config;
    const OFFICIAL_LABELS: Record<string, string> = { oni: 'ONI', pdo: 'NCEI PDO', pmm: 'Official PMM' };
    const MODEL_COLORS = ['#c792ea', '#7fdbca', '#f78c6c', '#82aaff', '#c3e88d', '#ffcb6b', '#ff5370'];

    let data: ModesData | null = null;
    let loading = true;
    let error: string | null = null;
    let loadedFrom: string | null = null;
    let urlInput = getDataUrl();

    let tab: Group = 'equatorial';
    let selectedId: string | null = null;
    let step: number | null = null;

    let showMembers = true;
    let showSpread = true;
    let showMean = true;
    let showModels = true;
    let showOfficial = false;
    let showDaily = true;
    let syncTimeline = true;
    let history: Record<string, number> = { monthly: 365, daily: 60 };

    let mapVisible = true;
    let mapSource: MapSource = 'week';
    let mapStep = 1;
    let allNino = false;

    let timestamp: number = store.get('timestamp');
    let layer: ModesMapLayer | null = null;
    let timestampListener: number | null = null;

    $: all = data ? MODES.map(m => seriesFor(data!, m)) : [];
    $: equatorial = all.filter(s => s.mode.group === 'equatorial');
    $: oscillations = all.filter(s => s.mode.group === 'oscillation');
    $: selected = all.find(s => s.mode.id === selectedId) || null;
    $: mapInfo = data ? mapValues(data, mapSource, mapStep) : null;

    $: if (layer) {
        layer.render(data, {
            visible: mapVisible,
            allNino,
            selected: selectedId,
            source: mapSource,
            step: mapStep,
        });
    }

    function historyChoices(m: ModeDef) {
        return m.freq === 'monthly'
            ? [
                  { label: '1 yr', days: 365 },
                  { label: '2 yr', days: 730 },
                  { label: '5 yr', days: 1800 },
              ]
            : [
                  { label: '30 d', days: 30 },
                  { label: '60 d', days: 60 },
                  { label: '120 d', days: 118 },
              ];
    }

    const historyFor = (m: ModeDef) => history[m.freq];

    function setHistory(m: ModeDef, days: number) {
        history = { ...history, [m.freq]: days };
    }

    /** "→ +1.2 by Dec" style outlook from the ensemble mean */
    function trend(s: ModeSeries, short = false): string {
        const fc = s.forecast;
        if (!fc || !fc.mean.length) {
            return '';
        }
        const k = s.mode.freq === 'monthly' ? Math.min(3, fc.mean.length - 1) : Math.min(7, fc.mean.length - 1);
        const v = fc.mean[k];
        if (v === null) {
            return '';
        }
        const when =
            s.mode.freq === 'monthly'
                ? new Date(`${fc.labels[k]}-15T00:00:00Z`).toLocaleDateString(undefined, { month: 'short', timeZone: 'UTC' })
                : `d+${k}`;
        return short ? `→ ${fmt(v, s.mode.id === 'pmm' ? 1 : 1)} ${when}` : `Forecast ${when}: ${fmt(v)}`;
    }

    function validationNote(id: string): string {
        const v = data?.validation;
        if (!v) {
            return '';
        }
        const note: Record<string, string> = {
            enso: v.nino34_vs_oni ? `Monthly Niño 3.4 vs CPC ONI 1982–2025: r = ${v.nino34_vs_oni}.` : '',
            iod: v.dmi_vs_hadisst ? `DMI vs HadISST DMI 1982–2025: r = ${v.dmi_vs_hadisst}.` : '',
            pdo: v.pdo_vs_ncei ? `PDO vs NCEI PDO 1950–2026: r = ${v.pdo_vs_ncei}.` : '',
            pmm: v.pmm_vs_vimont ? `PMM vs Chiang & Vimont index 1950–2026: r = ${v.pmm_vs_vimont}.` : '',
            amo: v.amo_vs_psl ? `vs PSL (Enfield) AMO 1950–2023: r = ${v.amo_vs_psl}.` : '',
        };
        return note[id] ? `${note[id]} ` : '';
    }

    function setTab(t: Group) {
        tab = t;
        if (selectedId && MODE_BY_ID[selectedId].group !== t) {
            selectedId = null;
        }
    }

    function select(id: string) {
        if (selectedId === id) {
            selectedId = null;
            return;
        }
        selectedId = id;
        const mode = MODE_BY_ID[id];
        tab = mode.group;
        // default step: 3 months / 7 days ahead
        const s = all.find(x => x.mode.id === id);
        const n = s?.forecast?.labels.length || 0;
        step = n ? Math.min(mode.freq === 'monthly' ? 3 : 7, n - 1) : null;
        if (mode.freq === 'daily' && syncTimeline && s?.forecast) {
            // follow Windy's timeline only when it has been moved past today
            const i = s.forecast.labels.indexOf(isoDay(timestamp));
            if (i > 0) {
                step = i;
            }
        }
    }

    function selectStep(i: number) {
        const s = selected;
        if (!s?.forecast) {
            return;
        }
        step = Math.max(0, Math.min(s.forecast.labels.length - 1, i));
        if (s.mode.freq === 'monthly') {
            if (s.mode.group === 'equatorial') {
                mapSource = 'forecast';
                mapStep = step;
            }
        } else if (syncTimeline) {
            const day = s.forecast.labels[step];
            if (day >= isoDay(Date.now())) {
                store.set('timestamp', dayTimestamp(day));
            }
        }
    }

    function onTimestamp(ts: number) {
        timestamp = ts;
        const s = selected;
        if (!syncTimeline || !s || s.mode.freq !== 'daily' || !s.forecast) {
            return;
        }
        const i = s.forecast.labels.indexOf(isoDay(ts));
        if (i >= 0 && i !== step) {
            step = i;
        }
    }

    function showSstLayer() {
        try {
            store.set('overlay', 'sst');
        } catch (e) {
            console.error('windy-plugin-climate-modes: cannot switch overlay', e);
        }
    }

    async function load() {
        loading = true;
        error = null;
        try {
            const res = await loadModesData();
            data = res.data;
            loadedFrom = res.url;
            if (!data.daily && mapSource === 'week') {
                mapSource = 'month';
            }
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    function saveUrl() {
        setDataUrl(urlInput.trim() || null);
        load();
    }

    function resetUrl() {
        setDataUrl(null);
        urlInput = getDataUrl();
        load();
    }

    /** Opening the plugin with a mode, e.g. from another plugin: { mode: 'enso' } */
    export const onopen = (params: unknown) => {
        const id = (params as { mode?: string } | undefined)?.mode;
        if (id && MODE_BY_ID[id] && data) {
            select(id);
        }
        if (!data && !loading) {
            load();
        }
    };

    onMount(() => {
        layer = new ModesMapLayer(id => {
            if (selectedId !== id) {
                select(id);
            }
        });
        timestampListener = store.on('timestamp', onTimestamp);
        load();
    });

    onDestroy(() => {
        if (timestampListener !== null) {
            store.off(timestampListener);
        }
        layer?.destroy();
        layer = null;
    });
</script>

<style lang="less">
    @pos: #ff6b4a;
    @neg: #4aa3ff;

    .cm {
        .muted {
            opacity: 0.65;
        }
        button:disabled {
            opacity: 0.3;
        }
    }
    .cm-msg {
        padding: 12px 0;
        &--error {
            color: #ff8a80;
            small {
                display: block;
                margin-top: 4px;
                opacity: 0.8;
                word-break: break-all;
            }
        }
    }
    .tabs {
        display: flex;
        gap: 4px;
        margin-bottom: 10px;
        &__btn {
            flex: 1;
            padding: 6px 0;
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 4px;
            background: transparent;
            color: inherit;
            cursor: pointer;
            &--on {
                background: rgba(255, 255, 255, 0.16);
                border-color: rgba(255, 255, 255, 0.6);
                font-weight: bold;
            }
        }
    }
    .cards {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 6px;
    }
    .card {
        padding: 8px 6px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-top: 3px solid #9aa3ad;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.04);
        color: inherit;
        text-align: left;
        cursor: pointer;
        &:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        &--pos {
            border-top-color: @pos;
        }
        &--neg {
            border-top-color: @neg;
        }
        &--sel {
            background: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.7);
        }
        &__name {
            font-size: 11px;
            opacity: 0.75;
        }
        &__val {
            font-size: 20px;
            font-weight: bold;
            line-height: 1.2;
            small {
                font-size: 11px;
                font-weight: normal;
                margin-left: 2px;
                opacity: 0.7;
            }
        }
        &--pos &__val {
            color: #ff8a70;
        }
        &--neg &__val {
            color: #7fbfff;
        }
        &__phase {
            font-size: 11px;
            line-height: 1.3;
            span {
                opacity: 0.7;
            }
        }
        &__sub {
            margin-top: 3px;
            font-size: 10px;
            opacity: 0.6;
            line-height: 1.35;
        }
    }
    .mapopts {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 4px 10px;
        margin: 8px 0 2px;
        label {
            cursor: pointer;
            white-space: nowrap;
        }
        select {
            max-width: 210px;
        }
    }
    .mapinfo {
        opacity: 0.6;
        margin-bottom: 6px;
    }
    .linkbtn {
        padding: 2px 8px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 10px;
        background: transparent;
        color: inherit;
        font-size: 11px;
        cursor: pointer;
    }
    .grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 5px;
    }
    .osc {
        padding: 6px 4px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-bottom: 3px solid #9aa3ad;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.04);
        color: inherit;
        cursor: pointer;
        text-align: center;
        &:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        &--pos {
            border-bottom-color: @pos;
        }
        &--neg {
            border-bottom-color: @neg;
        }
        &--sel {
            background: rgba(255, 255, 255, 0.16);
            border-color: rgba(255, 255, 255, 0.7);
        }
        &--na {
            opacity: 0.45;
        }
        &__name {
            font-weight: bold;
            font-size: 13px;
        }
        &__val {
            font-size: 15px;
            line-height: 1.3;
        }
        &--pos &__val {
            color: #ff8a70;
        }
        &--neg &__val {
            color: #7fbfff;
        }
        &__trend {
            font-size: 9px;
            opacity: 0.65;
            white-space: nowrap;
        }
    }
    .hint {
        margin: 12px 0;
        padding: 8px 10px;
        border-left: 3px solid rgba(255, 255, 255, 0.3);
        background: rgba(255, 255, 255, 0.04);
        opacity: 0.8;
        line-height: 1.5;
    }
    .detail {
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        &__head {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 4px;
            line-height: 1.45;
        }
        &__close {
            width: 26px;
            height: 26px;
            flex: 0 0 26px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 4px;
            background: transparent;
            color: inherit;
            font-size: 16px;
            line-height: 22px;
            cursor: pointer;
        }
    }
    .hist {
        display: flex;
        align-items: center;
        gap: 4px;
        margin: 4px 0 6px;
        opacity: 0.85;
    }
    .chip {
        padding: 1px 8px;
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 10px;
        background: transparent;
        color: inherit;
        font-size: 11px;
        cursor: pointer;
        &--on {
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.6);
        }
    }
    .probs {
        margin: 8px 0;
        &__title {
            margin-bottom: 3px;
        }
        &__bar {
            display: flex;
            height: 18px;
            border-radius: 3px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.08);
            font-size: 10px;
            line-height: 18px;
            text-align: center;
            color: #10151c;
            font-weight: bold;
        }
        &__neg {
            background: @neg;
        }
        &__neu {
            background: #c9d1da;
        }
        &__pos {
            background: @pos;
        }
        &__legend {
            display: flex;
            justify-content: space-between;
            margin-top: 2px;
            opacity: 0.8;
            .n {
                color: #7fbfff;
            }
            .p {
                color: #ff8a70;
            }
        }
    }
    .steps {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 4px;
        input {
            flex: 1;
        }
    }
    .day__btn {
        width: 26px;
        height: 24px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 4px;
        background: transparent;
        color: inherit;
        font-size: 16px;
        line-height: 20px;
        cursor: pointer;
    }
    .opts {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 4px 10px;
        margin: 8px 0;
        label {
            cursor: pointer;
            white-space: nowrap;
        }
    }
    .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 3px 12px;
        margin: 6px 0;
        opacity: 0.85;
        i {
            display: inline-block;
            width: 10px;
            height: 10px;
            margin-right: 4px;
            border-radius: 2px;
            vertical-align: -1px;
            &.dash {
                height: 0;
                border-top: 2px dashed;
                border-radius: 0;
                vertical-align: 3px;
            }
        }
    }
    .desc {
        margin: 6px 0;
        line-height: 1.5;
        opacity: 0.8;
    }
    .foot {
        margin-top: 8px;
        line-height: 1.5;
        opacity: 0.55;
    }
    .settings {
        margin-top: 10px;
        summary {
            cursor: pointer;
            opacity: 0.7;
        }
        input {
            width: 100%;
            margin: 6px 0;
        }
        &__row {
            display: flex;
            gap: 6px;
            margin-bottom: 4px;
        }
    }

    /* labels drawn on the main Windy map (outside this component's DOM) */
    :global(.cm-label-icon) {
        background: none;
        border: none;
    }
    :global(.cm-label) {
        display: inline-block;
        position: relative;
        left: 50%;
        transform: translateX(-50%);
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid;
        background: rgba(12, 16, 22, 0.85);
        color: #fff;
        font-size: 12px;
        line-height: 1.3;
        text-align: center;
        white-space: nowrap;
        text-shadow: none;
        cursor: pointer;
    }
    :global(.cm-label:hover) {
        background: rgba(40, 48, 60, 0.95);
    }
    :global(.cm-label--sel) {
        box-shadow: 0 0 0 2px #fff;
    }
    :global(.cm-label small) {
        display: block;
        font-size: 10px;
        opacity: 0.85;
    }
    :global(.cm-label .cm-val) {
        font-weight: bold;
    }
    :global(.cm-tag) {
        display: inline-block;
        position: relative;
        left: 50%;
        transform: translateX(-50%);
        padding: 0 5px;
        border-radius: 3px;
        background: rgba(0, 0, 0, 0.55);
        color: #fff;
        font-size: 10px;
        line-height: 16px;
        white-space: nowrap;
        text-shadow: none;
    }
</style>
