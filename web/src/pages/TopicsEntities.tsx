import { useMemo, useState } from "react";
import { ChartHead, EmbeddingScatter, HBar, Heatmap, Network } from "../components/charts";
import { CHAPTER_ORDER, CHAPTER_SHORT, type DataBundle, fmt } from "../data";
import { readVar } from "../theme";

const MODELS: [string, string][] = [["tfidf_nmf", "TF-IDF + NMF"], ["lda", "LDA"], ["embedding_kmeans", "Embeddings + k-means"]];

export function TopicsPage({ d }: { d: DataBundle }) {
  const [model, setModel] = useState("tfidf_nmf");
  const summary = d.topics.summary.filter((r: any) => r.model === model);
  const [topic, setTopic] = useState<number>(summary[0]?.topic ?? 0);
  const examples = d.topics.examples.filter((r: any) => r.model === model && r.topic === topic);
  const byCh = d.topics.by_chapter.filter((r: any) => r.model === model);
  const topics = summary.map((r: any) => r.topic).sort((a: number, b: number) => a - b);
  const [hl, setHl] = useState(CHAPTER_ORDER[2]);
  const status = d.meta.topics;
  const barData = summary.map((r: any) => ({ ...r, name: `T${r.topic}: ${r.top_terms.split(", ").slice(0, 3).join(", ")}`, pct: 100 * r.share_paragraphs }))
    .sort((a: any, b: any) => b.pct - a.pct);
  return (
    <>
      <h1>Temas y mapa semántico</h1>
      <p className="lede">Tres modelos de temas sobre {fmt(status.n_paragraphs_modelled)} párrafos, con k = {status.k} elegido por
        coherencia NPMI. Los temas no se nombran automáticamente: se muestran sus términos y párrafos de ejemplo.</p>
      <div className="note">Los tres modelos coinciden poco entre sí (ARI entre {fmt(Math.min(...d.topics.agreement.map((a: any) => a.adjusted_rand_index)), 2)} y{" "}
        {fmt(Math.max(...d.topics.agreement.map((a: any) => a.adjusted_rand_index)), 2)}), y la coherencia NPMI es baja en todos.
        Los “temas” dependen del modelo, así que los tratamos como descriptivos. BERTopic: {status.bertopic}. Embeddings:{" "}
        {d.meta.embedding_method}.</div>
      <div className="seg" style={{ margin: "8px 0 14px" }}>
        {MODELS.map(([k, n]) => <button key={k} className={model === k ? "on" : ""} onClick={() => { setModel(k); setTopic(0); }}>{n}</button>)}
      </div>
      <div className="grid grid-2">
        <div className="card">
          <ChartHead title="Distribución de temas" sub="% de párrafos cuyo tema dominante es cada uno." />
          <HBar data={barData} label="name" value="pct" fmtValue={(v) => `${v.toFixed(0)}%`} maxLabel={40} />
        </div>
        <div className="card">
          <ChartHead title="Párrafos de ejemplo" sub="Los tres párrafos con mayor peso en el tema." />
          <div className="controls"><select value={topic} onChange={(e) => setTopic(Number(e.target.value))}>
            {topics.map((t: number) => <option key={t} value={t}>T{t}: {summary.find((s: any) => s.topic === t)?.top_terms.split(", ").slice(0, 5).join(", ")}</option>)}
          </select></div>
          {examples.map((e: any) => <div key={e.paragraph_id} style={{ marginBottom: 12 }}>
            <div className="small muted">{e.paragraph_id} · p. {e.page} · peso {fmt(e.weight, 2)}</div>
            <blockquote className="small">{e.excerpt}…</blockquote>
            <div className="small muted">{e.section}</div></div>)}
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <ChartHead title="Temas por capítulo" sub="% de los párrafos de cada capítulo cuyo tema dominante es cada uno." />
        <Heatmap rows={CHAPTER_ORDER.filter((c) => byCh.some((r: any) => r.chapter === c))} cols={topics.map(String)}
          rowLabel={(r) => CHAPTER_SHORT[r]} colLabel={(c) => `T${c}`} fmtValue={(v) => v ? `${v.toFixed(0)}` : ""}
          value={(r, c) => 100 * (byCh.find((x: any) => x.chapter === r && String(x.dominant_topic) === c)?.share ?? 0)} />
      </div>
      <h2>Mapa semántico exploratorio</h2>
      <div className="card">
        <ChartHead title="Párrafos proyectados en 2D (UMAP)" sub="La distancia en el plano NO es una medida exacta de distancia semántica. Pase el cursor para leer el párrafo." />
        <div className="controls"><span className="small ink2">Resaltar:</span>
          <select value={hl} onChange={(e) => setHl(e.target.value)}>{CHAPTER_ORDER.map((c) => <option key={c} value={c}>{CHAPTER_SHORT[c]}</option>)}</select></div>
        <EmbeddingScatter points={d.embeddingMap} highlight={(p) => p.chapter === hl} />
      </div>
    </>
  );
}

const TYPES: [string, string, string][] = [["ORG", "Organización", "--series-1"], ["PERSON", "Persona", "--series-2"],
  ["GPE_LOC", "Lugar", "--series-3"], ["LAW", "Norma / sentencia", "--series-4"]];

export function EntitiesPage({ d }: { d: DataBundle }) {
  const [type, setType] = useState("ALL");
  const [q, setQ] = useState("");
  const [net, setNet] = useState<"entity" | "concept">("entity");
  const colorOfType = (t: string) => readVar(TYPES.find((x) => x[0] === t)?.[2] ?? "--muted");
  const rows = useMemo(() => d.entities.filter((e: any) => ["ORG", "PERSON", "GPE_LOC", "LAW"].includes(e.entity_type)
    && (type === "ALL" || e.entity_type === type) && (!q || e.entity.toLowerCase().includes(q.toLowerCase()))), [d, type, q]);
  return (
    <>
      <h1>Entidades y redes</h1>
      <p className="lede">Personas, organizaciones, lugares y normas mencionados, detectados con spaCy (español) y reglas.
        Los alias solo se fusionan cuando el propio documento define la sigla (“Unidad Nacional de Protección (UNP)”).</p>
      <div className="note">El reconocimiento automático comete errores (p. ej., fragmentos de nombres de ministerios
        etiquetados como lugares). Los términos genéricos (“Estado”, “Gobierno”) y la categoría MISC se excluyen de gráficos y
        redes; todas las menciones están en <code>entity_mentions.csv</code>.</div>
      <div className="grid grid-2">
        <div className="card">
          <ChartHead title="Entidades más mencionadas" />
          <div className="legend">{TYPES.map(([k, n, v]) => <span key={k}><i className="sw" style={{ background: readVar(v) }} />{n}</span>)}</div>
          <HBar data={rows.slice(0, 25)} label="entity" value="count" colorOf={(e) => colorOfType(e.entity_type)}
            tooltipExtra={(e) => `páginas: ${String(e.pages).split(";").slice(0, 12).join(", ")}`} maxLabel={40} />
        </div>
        <div className="card">
          <ChartHead title="Buscar entidades" />
          <div className="controls">
            <input type="search" placeholder="Buscar (p. ej., Contraloría, UNGRD)…" value={q} onChange={(e) => setQ(e.target.value)} />
            <select value={type} onChange={(e) => setType(e.target.value)}><option value="ALL">Todos los tipos</option>
              {TYPES.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select>
          </div>
          <div className="table-wrap" style={{ maxHeight: 520, overflowY: "auto" }}>
            <table><thead><tr><th>Entidad</th><th>Tipo</th><th className="num">Menciones</th><th>Páginas</th></tr></thead>
              <tbody>{rows.slice(0, 200).map((e: any) => <tr key={e.entity + e.entity_type}><td>{e.entity}{e.is_public_institution && <span className="muted small"> · institución pública</span>}</td>
                <td className="small">{TYPES.find((t) => t[0] === e.entity_type)?.[1]}</td><td className="num">{e.count}</td>
                <td className="small">{String(e.pages).split(";").slice(0, 8).join(", ")}{String(e.pages).split(";").length > 8 ? "…" : ""}</td></tr>)}</tbody></table>
          </div>
        </div>
      </div>
      <h2>Redes de coaparición</h2>
      <div className="card">
        <div className="seg" style={{ marginBottom: 8 }}>
          <button className={net === "entity" ? "on" : ""} onClick={() => setNet("entity")}>Entidades (mismo párrafo)</button>
          <button className={net === "concept" ? "on" : ""} onClick={() => setNet("concept")}>Conceptos (misma oración)</button>
        </div>
        <p className="chart-sub">Nodos más conectados; grosor de arista = número de coapariciones. Pase el cursor para aislar a los
          vecinos de un nodo. Las posiciones son ilustrativas.</p>
        {net === "entity"
          ? <Network key="e" graph={d.entityNetwork as any} topN={60} colorOf={(n) => colorOfType(n.entity_type)}
              legend={TYPES.map(([, n, v]) => [n, readVar(v)])} />
          : <Network key="c" graph={d.conceptNetwork as any} topN={50} />}
      </div>
    </>
  );
}
