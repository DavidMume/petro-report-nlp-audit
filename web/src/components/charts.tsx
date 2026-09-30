import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation } from "d3-force";
import { useColors } from "../theme";
import { fmt, STATUS_ES, STATUS_VAR } from "../data";

const axisTick = (c: ReturnType<typeof useColors>) => ({ fill: c.muted, fontSize: 11.5 });

export function Tip({ title, lines }: { title?: string; lines: (string | null | undefined)[] }) {
  return (
    <div className="tooltip">
      {title && <div className="t">{title}</div>}
      {lines.filter(Boolean).map((l, i) => <div key={i}>{l}</div>)}
    </div>
  );
}

export function ChartHead({ title, sub }: { title: string; sub?: string }) {
  return (
    <>
      <p className="chart-title">{title}</p>
      {sub && <p className="chart-sub">{sub}</p>}
    </>
  );
}

/** Horizontal bar chart: one series, value label at the bar tip, hover tooltip. */
export function HBar({ data, label, value, color, height, fmtValue, tooltipExtra, colorOf, maxLabel = 38 }: {
  data: any[]; label: string; value: string; color?: string; height?: number; fmtValue?: (v: number) => string;
  tooltipExtra?: (d: any) => string | null; colorOf?: (d: any) => string; maxLabel?: number;
}) {
  const c = useColors();
  const f = fmtValue ?? ((v: number) => fmt(v));
  const h = height ?? Math.max(160, data.length * 26 + 30);
  const short = (s: string) => (s && s.length > maxLabel ? s.slice(0, maxLabel - 1) + "…" : s);
  return (
    <ResponsiveContainer width="100%" height={h}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 48, bottom: 4, left: 4 }} barCategoryGap={6}>
        <CartesianGrid horizontal={false} stroke={c.grid} />
        <XAxis type="number" tick={axisTick(c)} axisLine={{ stroke: c.axis }} tickLine={false} tickFormatter={(v) => f(v)} />
        <YAxis type="category" dataKey={label} width={Math.min(280, maxLabel * 7)} tick={{ fill: c.ink2, fontSize: 12 }}
          tickFormatter={short} axisLine={false} tickLine={false} interval={0} />
        <Tooltip cursor={{ fill: c.grid, opacity: 0.4 }}
          content={({ active, payload }) => active && payload?.length ? (
            <Tip title={String(payload[0].payload[label])}
              lines={[f(payload[0].payload[value]), tooltipExtra?.(payload[0].payload)]} />) : null} />
        <Bar dataKey={value} maxBarSize={20} radius={[0, 4, 4, 0]} fill={color ?? c.series[0]}
          label={{ position: "right", fill: c.ink2, fontSize: 11.5, formatter: (v: any) => f(Number(v)) }}>
          {colorOf && data.map((d, i) => <Cell key={i} fill={colorOf(d)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Page-by-page structure map (one bar per page, coloured by chapter). */
export function StructureMap({ data, chapters }: { data: { page: number; chapter: string; n_words: number }[]; chapters: string[] }) {
  const c = useColors();
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }} barCategoryGap={1}>
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey="page" tick={axisTick(c)} axisLine={{ stroke: c.axis }} tickLine={false} interval={9} />
        <YAxis tick={axisTick(c)} axisLine={false} tickLine={false} width={36} />
        <Tooltip cursor={{ fill: c.grid, opacity: 0.4 }}
          content={({ active, payload }) => active && payload?.length ? (
            <Tip title={`Página ${payload[0].payload.page}`} lines={[payload[0].payload.chapter, `${fmt(payload[0].payload.n_words)} palabras`]} />) : null} />
        <Bar dataKey="n_words" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => <Cell key={i} fill={c.series[Math.max(0, chapters.indexOf(d.chapter))]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Heatmap as an HTML grid (keyboard/table friendly). values in [0, max]. */
export function Heatmap({ rows, cols, value, fmtValue, colLabel, rowLabel }: {
  rows: string[]; cols: string[]; value: (r: string, c: string) => number; fmtValue?: (v: number) => string;
  colLabel?: (c: string) => string; rowLabel?: (r: string) => string;
}) {
  const colors = useColors();
  const all = rows.flatMap((r) => cols.map((c) => value(r, c)));
  const max = Math.max(...all, 1e-9);
  const f = fmtValue ?? ((v: number) => v.toFixed(1));
  const shade = (v: number) => {
    const t = v / max;
    return `color-mix(in srgb, ${colors.seq[3]} ${Math.round(t * 100)}%, ${colors.seq[0]})`;
  };
  return (
    <div className="table-wrap">
      <table style={{ tableLayout: "fixed", minWidth: cols.length * 64 + 170 }}>
        <thead>
          <tr><th style={{ width: 170 }} />{cols.map((c) => <th key={c} className="small" style={{ fontWeight: 500 }}>{colLabel ? colLabel(c) : c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <th className="small">{rowLabel ? rowLabel(r) : r}</th>
              {cols.map((c) => {
                const v = value(r, c);
                const dark = v / max > 0.55;
                return (
                  <td key={c} title={`${rowLabel ? rowLabel(r) : r} · ${colLabel ? colLabel(c) : c}: ${f(v)}`}
                    style={{ background: shade(v), color: dark ? "#fff" : colors.ink, textAlign: "center",
                      fontSize: 12, border: `2px solid ${colors.surface}` }} className="tnum">{f(v)}</td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Force-directed network (layout computed once in the browser, then static). */
export function Network({ graph, topN = 60, colorOf, legend }: {
  graph: { nodes: any[]; links: any[] }; topN?: number; colorOf?: (n: any) => string; legend?: [string, string][];
}) {
  const c = useColors();
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(800);
  const [hover, setHover] = useState<any | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const H = 520;
  const { nodes, links } = useMemo(() => {
    const keep = [...graph.nodes].sort((a, b) => b.weighted_degree - a.weighted_degree).slice(0, topN);
    const ids = new Set(keep.map((n) => n.id));
    const nodes = keep.map((n) => ({ ...n }));
    const links = graph.links.filter((l) => ids.has(l.source) && ids.has(l.target)).map((l) => ({ ...l }));
    const maxW = Math.max(...links.map((l) => l.weight), 1);
    const sim = forceSimulation(nodes as any)
      .force("link", forceLink(links as any).id((d: any) => d.id).distance((l: any) => 70 - 30 * (l.weight / maxW)).strength(0.4))
      .force("charge", forceManyBody().strength(-120))
      .force("center", forceCenter(0, 0))
      .force("collide", forceCollide().radius((d: any) => 6 + Math.sqrt(d.count) * 2.2))
      .stop();
    for (let i = 0; i < 300; i++) sim.tick();
    return { nodes, links };
  }, [graph, topN]);
  const xs = nodes.map((n: any) => n.x), ys = nodes.map((n: any) => n.y);
  const pad = 40, minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const sx = (x: number) => pad + ((x - minX) / (maxX - minX || 1)) * (w - 2 * pad);
  const sy = (y: number) => pad + ((y - minY) / (maxY - minY || 1)) * (H - 2 * pad);
  const maxWt = Math.max(...links.map((l: any) => l.weight), 1);
  const labelled = new Set([...nodes].sort((a: any, b: any) => b.weighted_degree - a.weighted_degree).slice(0, 14).map((n: any) => n.id));
  const neighbours = useMemo(() => {
    if (!hover) return null;
    const s = new Set<string>([hover.id]);
    links.forEach((l: any) => { if (l.source.id === hover.id) s.add(l.target.id); if (l.target.id === hover.id) s.add(l.source.id); });
    return s;
  }, [hover, links]);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      {legend && <div className="legend">{legend.map(([k, col]) => <span key={k}><i className="sw" style={{ background: col, borderRadius: "50%" }} />{k}</span>)}</div>}
      <svg width={w} height={H} role="img" aria-label="Red de coaparición">
        {links.map((l: any, i: number) => {
          const on = !neighbours || (neighbours.has(l.source.id) && neighbours.has(l.target.id));
          return <line key={i} x1={sx(l.source.x)} y1={sy(l.source.y)} x2={sx(l.target.x)} y2={sy(l.target.y)}
            stroke={c.axis} strokeOpacity={on ? 0.9 : 0.15} strokeWidth={0.6 + 2 * (l.weight / maxWt)} />;
        })}
        {nodes.map((n: any) => {
          const on = !neighbours || neighbours.has(n.id);
          const r = 4 + Math.sqrt(n.count) * 1.8;
          return (
            <g key={n.id} onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(null)} style={{ cursor: "default" }}
              opacity={on ? 1 : 0.25}>
              <circle cx={sx(n.x)} cy={sy(n.y)} r={Math.max(r + 6, 12)} fill="transparent" />
              <circle cx={sx(n.x)} cy={sy(n.y)} r={r} fill={colorOf ? colorOf(n) : c.series[0]} stroke={c.surface} strokeWidth={2} />
              {(labelled.has(n.id) || hover?.id === n.id) && (
                <text x={sx(n.x) + r + 4} y={sy(n.y) + 4} fontSize={11.5} fill={c.ink}
                  style={{ paintOrder: "stroke", stroke: c.surface, strokeWidth: 3 }}>{n.id.length > 32 ? n.id.slice(0, 31) + "…" : n.id}</text>
              )}
            </g>
          );
        })}
      </svg>
      {hover && (
        <div style={{ position: "absolute", left: Math.min(sx(hover.x) + 14, w - 240), top: sy(hover.y) + 10, pointerEvents: "none" }}>
          <Tip title={hover.id} lines={[`${fmt(hover.count)} menciones`, `grado ponderado ${fmt(hover.weighted_degree)}`,
            hover.entity_type ? `tipo: ${hover.entity_type}` : null]} />
        </div>
      )}
    </div>
  );
}

/** 2D embedding scatter: highlighted group in accent, rest de-emphasised. */
export function EmbeddingScatter({ points, highlight }: { points: any[]; highlight: (p: any) => boolean }) {
  const c = useColors();
  const hi = points.filter(highlight), lo = points.filter((p) => !highlight(p));
  return (
    <ResponsiveContainer width="100%" height={440}>
      <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
        <XAxis type="number" dataKey="x" hide domain={["dataMin", "dataMax"]} />
        <YAxis type="number" dataKey="y" hide domain={["dataMin", "dataMax"]} />
        <ZAxis range={[36, 36]} />
        <Tooltip cursor={false} content={({ active, payload }) => active && payload?.length ? (
          <Tip title={`${payload[0].payload.paragraph_id} · p. ${payload[0].payload.page}`}
            lines={[payload[0].payload.level2, (payload[0].payload.excerpt || "").slice(0, 160) + "…"]} />) : null} />
        <Scatter data={lo} fill={c.deemph} isAnimationActive={false} />
        <Scatter data={hi} fill={c.series[0]} stroke={c.surface} strokeWidth={1} isAnimationActive={false} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function SeriesLine({ data, x, y, refLines, xLabel }: { data: any[]; x: string; y: string; refLines?: { x: string; label: string; strong?: boolean }[]; xLabel?: (d: any) => string }) {
  const c = useColors();
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 20, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey={x} tick={axisTick(c)} axisLine={{ stroke: c.axis }} tickLine={false} interval={5} />
        <YAxis tick={axisTick(c)} axisLine={false} tickLine={false} width={36} />
        <Tooltip content={({ active, payload }) => active && payload?.length ? (
          <Tip title={String(payload[0].payload[x])} lines={[xLabel?.(payload[0].payload), `${y}: ${fmt(payload[0].payload[y], 2)}`]} />) : null} />
        {refLines?.map((r) => <ReferenceLine key={r.x} x={r.x} stroke={r.strong ? c.series[1] : c.axis}
          strokeWidth={r.strong ? 2 : 1} label={{ value: r.label, position: "top", fill: c.ink2, fontSize: 11 }} />)}
        <Line dataKey={y} stroke={c.series[0]} strokeWidth={2} dot={{ r: 3, fill: c.series[0], stroke: c.surface, strokeWidth: 2 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const col = getComputedStyle(document.documentElement).getPropertyValue(STATUS_VAR[status] ?? "--st-unassessed");
  return <span className="badge"><i className="dot" style={{ background: col }} />{STATUS_ES[status] ?? status}</span>;
}

export function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return <div className="tile"><div className="label">{label}</div><div className="value">{value}</div>{sub && <div className="sub">{sub}</div>}</div>;
}
