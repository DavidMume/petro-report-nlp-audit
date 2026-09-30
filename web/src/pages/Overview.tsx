import { useMemo } from "react";
import { ChartHead, StructureMap, Tile } from "../components/charts";
import { CHAPTER_ORDER, CHAPTER_SHORT, CHAPTER_VAR, type DataBundle, fmt, STATUS_ES } from "../data";
import { readVar } from "../theme";

export function Overview({ d, go }: { d: DataBundle; go: (r: string) => void }) {
  const s = d.meta.stats;
  const cov = Object.fromEntries(d.meta.coverage.map((r: any) => [r.metric, r.value]));
  const assessed = d.claims.filter((c) => c.verification_status !== "unassessed");
  const byStatus = useMemo(() => {
    const m: Record<string, number> = {};
    assessed.forEach((c) => (m[c.verification_status] = (m[c.verification_status] || 0) + 1));
    return m;
  }, [assessed]);
  const pages = useMemo(() => {
    const byPage: Record<number, { page: number; chapter: string; n_words: number }> = {};
    for (let p = 1; p <= d.meta.source.pages; p++) byPage[p] = { page: p, chapter: "", n_words: 0 };
    d.wordsPerPage.forEach((r: any) => { byPage[r.page].n_words += r.n_words; byPage[r.page].chapter = r.chapter; });
    return Object.values(byPage);
  }, [d]);
  const robustCp = d.stylometry.change_points.filter((c: any) => c.robust).length;
  const prov = d.stylometry.provenance_statements.length;

  return (
    <>
      <section className="hero">
        <div className="kicker">Auditoría computacional reproducible · NLP · verificación documental</div>
        <h1>¿Qué afirma “El Libro de la Verdad”, cómo lo afirma y qué tan bien se sostiene?</h1>
        <p className="lede">
          Análisis del documento publicado en 2026 por el Gobierno de Colombia (Empalme Anticorrupción 2026) sobre la
          administración 2022–2026. Separamos tres preguntas: qué dice el informe, cómo construye su argumento y qué
          ocurre cuando sus afirmaciones se contrastan con evidencia externa. No producimos una calificación global del
          informe ni de ningún gobierno.
        </p>
      </section>

      <div className="tiles">
        <Tile label="Páginas del PDF" value={fmt(d.meta.source.pages)} sub={`SHA-256 ${String(d.meta.source.sha256).slice(0, 10)}…`} />
        <Tile label="Palabras analizadas" value={fmt(s.words)} sub={`${fmt(s.sentences)} oraciones`} />
        <Tile label="Afirmaciones candidatas" value={fmt(cov.claim_candidates_total)} sub={`${fmt(cov.factual_candidates)} fácticas · sin revisión humana`} />
        <Tile label="Verificadas (piloto)" value={fmt(cov.assessed_total)} sub={`${fmt(cov.assessed_share_of_factual_candidates_pct, 1)}% de las fácticas`} />
      </div>

      <div className="card">
        <ChartHead title="Mapa estructural: palabras por página, coloreadas por capítulo"
          sub="Páginas vacías = cubierta, portadillas o páginas solo con imagen. Pase el cursor para ver cada página." />
        <div className="legend">
          {CHAPTER_ORDER.map((c, i) => <span key={c}><i className="sw" style={{ background: readVar(CHAPTER_VAR[i]) }} />{CHAPTER_SHORT[c]}</span>)}
        </div>
        <StructureMap data={pages} chapters={CHAPTER_ORDER} />
      </div>

      <h2>Lo que muestran los datos (hasta ahora)</h2>
      <div className="grid grid-3">
        <div className="card">
          <h3>1 · Qué dice</h3>
          <p className="small ink2">
            El texto se concentra en los capítulos II (comportamientos críticos, 59 casos) y IV (balance de 20 sectores).
            {" "}{fmt(s.sentences_with_numbers)} de {fmt(s.sentences)} oraciones contienen cifras; el vocabulario más
            frecuente es presupuestal (“millón”, “recurso”, “billón”, “contrato”).
          </p>
          <a href="#/nlp" onClick={(e) => { e.preventDefault(); go("nlp"); }}>Ver NLP →</a>
        </div>
        <div className="card">
          <h3>2 · Cómo lo dice</h3>
          <p className="small ink2">
            Las cartas preliminares y el capítulo V concentran el lenguaje evaluativo, adversarial (“gobierno
            saliente”, “régimen anterior”) y de restauración; el capítulo III, de hallazgos de corrupción, es el más
            atributivo (“según…”, “la Contraloría reveló…”) y el menos evaluativo. Son conteos de léxico exploratorios:
            describen uso de palabras, no intención ni sesgo.
          </p>
          <a href="#/nlp" onClick={(e) => { e.preventDefault(); go("nlp"); }}>Ver marcos y causalidad →</a>
        </div>
        <div className="card">
          <h3>3 · Qué tan bien se sostiene</h3>
          <p className="small ink2">
            Piloto de {assessed.length} afirmaciones:{" "}
            {Object.entries(byStatus).map(([k, v]) => `${v} ${STATUS_ES[k].toLowerCase()}`).join(", ")}.
            Las cifras suelen coincidir con fuentes oficiales, pero varias omiten contexto (línea base, métrica elegida,
            tipo de fuente). El piloto no es una muestra aleatoria: no se extrapola al informe completo.
          </p>
          <a href="#/verificacion" onClick={(e) => { e.preventDefault(); go("verificacion"); }}>Ver verificación →</a>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Procedencia lingüística (exploratorio)</h3>
          <p className="small ink2">
            El propio documento declara el uso de herramientas de inteligencia artificial para organizar y procesar
            información ({prov} párrafos lo mencionan, cap. I). La estilometría no encontró cambios de estilo robustos
            dentro del documento ({robustCp} puntos de cambio robustos); las señales más débiles coinciden con límites de
            capítulo. No se ejecutó ningún detector de IA: no hay uno calibrado para español en este proyecto.
          </p>
          <a href="#/procedencia" onClick={(e) => { e.preventDefault(); go("procedencia"); }}>Ver análisis →</a>
        </div>
        <div className="card">
          <h3>Cómo leer este sitio</h3>
          <p className="small ink2">
            Cada afirmación se puede rastrear: <strong>afirmación → pasaje original → página → fuente citada por el informe →
            evidencia externa → evaluación → confianza</strong>. Las evaluaciones del piloto fueron preparadas por un asistente de
            IA con las fuentes citadas y están pendientes de revisión humana.
          </p>
          <a href="#/afirmaciones" onClick={(e) => { e.preventDefault(); go("afirmaciones"); }}>Explorar afirmaciones →</a>
        </div>
      </div>
    </>
  );
}
