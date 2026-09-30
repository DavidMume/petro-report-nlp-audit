import { ChartHead, SeriesLine } from "../components/charts";
import { Markdown } from "../components/Markdown";
import { CHAPTER_SHORT, type DataBundle, fmt, REPO_URL, SOURCE_TYPE_ES } from "../data";

export function ProvenancePage({ d }: { d: DataBundle }) {
  const st = d.stylometry;
  const segs = st.segments.map((s: any) => ({ ...s, page0: String(s.pages).split("-")[0] }));
  const cps = st.change_points as any[];
  const bounds = segs.filter((s: any, i: number) => i > 0 && s.chapter !== segs[i - 1].chapter).map((s: any) => s.segment_id);
  const refLines = [
    ...bounds.map((b: string) => ({ x: b, label: "", strong: false })),
    ...cps.map((c) => ({ x: c.break_before_segment, label: `${c.n_configs_detected}/${c.n_configs}`, strong: true })),
  ];
  const outliers = segs.filter((s: any) => s.flag_stylistic_outlier);
  const best = [...st.clustering].sort((a: any, b: any) => b.silhouette - a.silhouette)[0];
  return (
    <>
      <h1>Análisis de procedencia lingüística</h1>
      <p className="lede">¿Hay cambios de estilo dentro del documento compatibles con varios procesos de escritura, edición
        o asistencia automatizada? Es un análisis exploratorio: la estilometría no identifica autores ni prueba el uso de IA.</p>

      <div className="card">
        <h3>Lo que el documento dice de sí mismo</h3>
        <p className="small ink2">La evidencia más fuerte sobre uso de IA es la declaración de los autores, no un detector. El
          capítulo I describe el uso de “instrumentos auxiliares de inteligencia artificial” para organización documental,
          consolidación analítica, priorización, trazabilidad, procesamiento de información y “organización de los insumos de
          los productos finales”, y afirma que no reemplazan la responsabilidad humana. No dice si la IA redactó texto.</p>
        {st.provenance_statements.map((p: any) => <div key={p.paragraph_id} style={{ marginBottom: 10 }}>
          <div className="small muted">{p.paragraph_id} · p. {p.page}</div><blockquote className="small">{p.clean_text}</blockquote></div>)}
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Detectores de IA</h3>
          <p className="small"><strong>No ejecutados.</strong> {d.meta.ai_detectors.reason}</p>
          <p className="small muted">Antes de usar cualquier detector sobre el informe hace falta un experimento de calibración en
            español con corpus humano (2015–2021), generado y híbrido, que reporte falsos positivos y negativos.</p>
        </div>
        <div className="card">
          <h3>Conclusiones permitidas y no permitidas</h3>
          <ul className="small">
            <li>✓ “Estos segmentos presentan diferencias estilísticas respecto al resto del documento.”</li>
            <li>✓ “No existe evidencia suficiente para atribuir estos segmentos de manera concluyente a una herramienta de IA.”</li>
            <li>✗ “ChatGPT escribió esta página.”</li>
            <li>✗ “El informe fue escrito en un X % por inteligencia artificial.”</li>
          </ul>
        </div>
      </div>

      <h2>Consistencia estilística interna</h2>
      <p className="small ink2">{segs.length} segmentos de unas 700 palabras que nunca cruzan capítulos; más de 100 rasgos
        (longitud de oración, diversidad léxica, palabras funcionales, puntuación, categorías gramaticales, legibilidad,
        conectores, atenuación, patrones de superficie).</p>
      <div className="card">
        <ChartHead title="Componente estilométrico principal a lo largo del documento"
          sub="Líneas grises = límites de capítulo; naranjas = puntos de cambio (n de 12 configuraciones que los detectan)." />
        <SeriesLine data={segs} x="segment_id" y="pc1" refLines={refLines} xLabel={(s) => `pp. ${s.pages} · ${CHAPTER_SHORT[s.chapter]}`} />
        <p className="small ink2">Ningún punto de cambio es robusto: el más frecuente aparece en{" "}
          {Math.max(...cps.map((c) => c.n_configs_detected), 0)} de 12 configuraciones, y los más frecuentes coinciden con el
          inicio de los capítulos III y IV, es decir, con cambios de género textual (casos de corrupción; balances firmados por
          cada ministro). El agrupamiento estilístico se alinea solo moderadamente con los capítulos (ARI {fmt(best?.ari_vs_chapters, 2)},
          silueta {fmt(best?.silhouette, 2)}).</p>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Segmentos atípicos</h3>
        <p className="small muted">Distancia de Mahalanobis &gt; χ² al 97,5 %. Un segmento atípico es distinto en estilo; eso no dice nada de quién lo escribió.</p>
        <table><thead><tr><th>Segmento</th><th>Páginas</th><th>Sección</th><th className="num">Mahalanobis²</th></tr></thead>
          <tbody>{outliers.map((s: any) => <tr key={s.segment_id}><td>{s.segment_id}</td><td>{s.pages}</td><td className="small">{s.section}</td><td className="num">{fmt(s.mahalanobis_sq, 1)}</td></tr>)}</tbody></table>
        <p className="small ink2">El segmento de preliminares reúne el índice y las cartas firmadas (un género distinto); el de
          las pp. 51–53 contiene casos de riesgo litigioso con citas normativas densas.</p>
      </div>
    </>
  );
}

const FILES: [string, string][] = [
  ["data/raw/Libro-De-La-Verdad.pdf", "Documento original (inmutable; SHA-256 en documents/source_metadata.json)"],
  ["data/processed/corpus.csv", "Corpus por oración: documento, página, sección, párrafo, oración, texto crudo/limpio/lematizado"],
  ["data/processed/paragraphs.csv", "Corpus por párrafo/bloque con tipo de bloque"],
  ["data/processed/claims.csv", "Afirmaciones candidatas (esquema completo)"],
  ["data/processed/numeric_claims.csv", "Cifras de las afirmaciones + reconstrucciones"],
  ["data/processed/claim_evidence.csv", "Evidencia externa por afirmación"],
  ["data/processed/claim_assessments.csv", "Evaluaciones del piloto"],
  ["sources/evidence_ledger.csv", "Registro completo de fuentes (URL, fechas, tipo)"],
  ["outputs/tables/entities.csv", "Entidades con menciones, páginas y secciones"],
  ["outputs/tables/topics_summary.csv", "Temas de los tres modelos"],
  ["outputs/tables/causal_sentences.csv", "Oraciones con lenguaje causal"],
  ["outputs/tables/stylometry_features.csv", "Rasgos estilométricos por segmento"],
  ["outputs/networks/entity_network.graphml", "Red de entidades (GraphML)"],
  ["outputs/data_manifest.json", "Manifiesto: hash, filas, columnas y script de cada dataset"],
];

export function DataPage({ d }: { d: DataBundle }) {
  return (
    <>
      <h1>Datos y reproducibilidad</h1>
      <p className="lede">Todo lo que muestra este sitio se regenera con <code>make all</code> a partir del PDF original. Las
        versiones de las dependencias están fijadas en <code>requirements.lock</code>.</p>
      <div className="card table-wrap"><table><thead><tr><th>Archivo</th><th>Contenido</th></tr></thead>
        <tbody>{FILES.map(([f, desc]) => <tr key={f}><td className="mono"><a href={`${REPO_URL}/blob/main/${f}`} target="_blank" rel="noreferrer">{f}</a></td><td className="small">{desc}</td></tr>)}</tbody></table></div>
      <h2>Pipeline</h2>
      <div className="card"><pre className="mono" style={{ whiteSpace: "pre-wrap", margin: 0 }}>{`make extract     # PDF → páginas (PyMuPDF → pdfplumber → OCR), verifica SHA-256
make corpus      # párrafos, oraciones, secciones; encabezados/pies registrados
make nlp         # frecuencias, TF-IDF, n-gramas, NER, redes, temas, embeddings, marcos
make claims      # afirmaciones candidatas, cifras, tabla causal
make validation  # verifica que cada evaluación cite evidencia externa
make authorship  # estilometría exploratoria
make charts      # 26 gráficos + manifiesto
make web-data    # JSON de este sitio`}</pre></div>
      <p className="small muted" style={{ marginTop: 12 }}>Datos generados: {d.meta.generated_at}. Modelo lingüístico: {d.meta.stats.spacy_model}.</p>
    </>
  );
}

export function MethodologyPage({ d }: { d: DataBundle }) {
  return (
    <>
      <div className="card"><Markdown source={d.methodology.markdown} /></div>
      {d.methodology.limitations && <div className="card" style={{ marginTop: 16 }}><Markdown source={d.methodology.limitations} /></div>}
    </>
  );
}

export function SourcesPage({ d }: { d: DataBundle }) {
  return (
    <>
      <h1>Fuentes</h1>
      <p className="lede">Registro de todas las fuentes externas consultadas, con fecha de consulta. La cobertura de prensa sobre
        el propio informe se registra, pero nunca se usa como evidencia (sería circular).</p>
      <div className="card table-wrap"><table><thead><tr><th>ID</th><th>Título</th><th>Organización</th><th>Tipo</th><th>Publicación</th><th>Consulta</th><th>Afirmaciones</th></tr></thead>
        <tbody>{d.ledger.map((l: any) => <tr key={l.source_id}><td>{l.source_id}</td>
          <td className="small">{l.url ? <a href={l.url} target="_blank" rel="noreferrer">{l.title}</a> : l.title}<div className="muted">{l.notes}</div></td>
          <td className="small">{l.organisation}</td><td className="small">{SOURCE_TYPE_ES[l.source_type] ?? l.source_type}</td>
          <td className="small">{l.publication_date || "—"}</td><td className="small">{l.access_date}</td><td className="small">{l.claim_ids || "—"}</td></tr>)}</tbody></table></div>
    </>
  );
}
