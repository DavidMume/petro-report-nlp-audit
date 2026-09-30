import { useEffect, useMemo, useState } from "react";
import { StatusBadge } from "../components/charts";
import { CHAPTER_ORDER, CHAPTER_SHORT, type Claim, type DataBundle, fmt, SOURCE_TYPE_ES, STATUS_ES, STATUS_ORDER, TYPE_ES } from "../data";

function highlight(text: string, sentence: string) {
  const i = text.indexOf(sentence);
  if (i < 0) return <>{text}</>;
  return <>{text.slice(0, i)}<mark>{sentence}</mark>{text.slice(i + sentence.length)}</>;
}

export function ClaimsPage({ d, initial }: { d: DataBundle; initial?: string }) {
  const [q, setQ] = useState("");
  const [type, setType] = useState("ALL");
  const [chapter, setChapter] = useState("ALL");
  const [kind, setKind] = useState("factual_candidate");
  const [status, setStatus] = useState(initial ? "ALL" : "ALL");
  const [prio, setPrio] = useState("ALL");
  const [causal, setCausal] = useState(false);
  const [sel, setSel] = useState<string | null>(initial ?? null);

  const paraById = useMemo(() => Object.fromEntries(d.paragraphs.map((p) => [p.paragraph_id, p])), [d]);
  const evByClaim = useMemo(() => {
    const m: Record<string, any[]> = {};
    d.evidence.forEach((e: any) => (m[e.claim_id] ||= []).push(e));
    return m;
  }, [d]);
  const ledger = useMemo(() => Object.fromEntries(d.ledger.map((l: any) => [l.source_id, l])), [d]);

  const rows = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return d.claims.filter((c) =>
      (kind === "ALL" || c.claim_kind === kind) && (type === "ALL" || c.claim_type === type) &&
      (chapter === "ALL" || c.chapter === chapter) && (status === "ALL" || c.verification_status === status) &&
      (prio === "ALL" || c.priority === prio) && (!causal || c.is_causal) &&
      (!qq || c.claim_text.toLowerCase().includes(qq) || c.claim_id.toLowerCase() === qq || (c.section || "").toLowerCase().includes(qq)))
      .sort((a, b) => (a.verification_status === "unassessed" ? 1 : 0) - (b.verification_status === "unassessed" ? 1 : 0) || a.page - b.page);
  }, [d, q, type, chapter, kind, status, prio, causal]);

  useEffect(() => { if (!sel && rows.length) setSel(rows[0].claim_id); }, [rows, sel]);
  const c: Claim | undefined = d.claims.find((x) => x.claim_id === sel);
  const para = c ? paraById[c.paragraph_id] : null;
  const ev = c ? evByClaim[c.claim_id] || [] : [];

  return (
    <>
      <h1>Explorador de afirmaciones</h1>
      <p className="lede">{fmt(d.claims.length)} afirmaciones candidatas extraídas con reglas (cifras, fechas, comparaciones,
        instituciones, atribuciones). Son <em>candidatas</em>: ninguna se ha revisado manualmente como afirmación definitiva.</p>
      <div className="controls">
        <input type="search" placeholder="Buscar texto, sección o ID (p. ej., UNGRD, C0465)…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="ALL">Todas</option><option value="factual_candidate">Fácticas</option><option value="evaluative_candidate">Evaluativas</option></select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="ALL">Cualquier estado</option>
          {STATUS_ORDER.map((s) => <option key={s} value={s}>{STATUS_ES[s]}</option>)}</select>
        <select value={type} onChange={(e) => setType(e.target.value)}><option value="ALL">Todos los tipos</option>
          {Object.entries(TYPE_ES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <select value={chapter} onChange={(e) => setChapter(e.target.value)}><option value="ALL">Todos los capítulos</option>
          {CHAPTER_ORDER.map((k) => <option key={k} value={k}>{CHAPTER_SHORT[k]}</option>)}</select>
        <select value={prio} onChange={(e) => setPrio(e.target.value)}><option value="ALL">Prioridad</option>
          <option value="A">A (más señales)</option><option value="B">B</option><option value="C">C</option></select>
        <label className="small ink2"><input type="checkbox" checked={causal} onChange={(e) => setCausal(e.target.checked)} /> solo lenguaje causal</label>
        <span className="small muted">{rows.length} resultados</span>
      </div>
      <div className="explorer">
        <div className="claim-list" role="listbox" aria-label="Afirmaciones">
          {rows.slice(0, 400).map((r) => (
            <div key={r.claim_id} role="option" aria-selected={r.claim_id === sel} tabIndex={0}
              className={"claim-item" + (r.claim_id === sel ? " sel" : "")}
              onClick={() => setSel(r.claim_id)} onKeyDown={(e) => e.key === "Enter" && setSel(r.claim_id)}>
              <div className="meta"><span className="mono">{r.claim_id}</span><span>p. {r.page}</span><span>{TYPE_ES[r.claim_type]}</span>
                {r.verification_status !== "unassessed" && <StatusBadge status={r.verification_status} />}</div>
              <div className="txt">{r.claim_text}</div>
            </div>
          ))}
          {rows.length > 400 && <div className="claim-item muted small">Mostrando 400 de {rows.length}. Refine la búsqueda.</div>}
        </div>
        <div className="card chain">
          {!c ? <p className="muted">Seleccione una afirmación.</p> : (
            <>
              <div className="step"><div className="k">Afirmación · {c.claim_id}</div>
                <div style={{ fontFamily: "var(--serif)", fontSize: 16 }}>{c.claim_text}</div>
                <div className="small muted" style={{ marginTop: 4 }}>
                  {TYPE_ES[c.claim_type]} · {c.claim_kind === "factual_candidate" ? "fáctica candidata" : "evaluativa candidata"} ·
                  prioridad {c.priority} · señales: {c.cues || "—"}{c.is_causal ? " · lenguaje causal" : ""}
                  {c.numeric_value !== null && ` · cifra principal: ${fmt(c.numeric_value, 2)} ${c.unit ?? ""}`}
                  {c.time_period && ` · periodo: ${c.time_period}`}</div></div>
              <div className="step"><div className="k">Pasaje original</div>
                {para ? <blockquote className="small">{highlight(para.clean_text, c.claim_text)}</blockquote> : <span className="muted">—</span>}</div>
              <div className="step"><div className="k">Página y sección</div>
                <div className="small">Página {c.page} del PDF · {c.section}</div>
                <div className="small muted mono">{c.paragraph_id} / {c.sentence_id}</div></div>
              <div className="step"><div className="k">Fuente citada por el informe</div>
                <div className="small">{c.source_cited_in_report || <span className="muted">No hay una fuente explícita en la oración (puede estar en el párrafo).</span>}</div></div>
              <div className="step"><div className="k">Evidencia externa</div>
                {ev.length === 0 ? <div className="small muted">Aún no se ha buscado evidencia externa para esta afirmación.</div> :
                  ev.map((e: any, i: number) => {
                    const l = ledger[e.source_id] || {};
                    const role = [e.supports && "respalda", e.contradicts && "contradice", e.contextualises && "contextualiza"].filter(Boolean).join(" · ");
                    return (
                      <div key={i} style={{ marginBottom: 10 }}>
                        <div className="small"><strong>{e.source_id}</strong> · {l.organisation || e.source_name} ·{" "}
                          <span className="muted">{SOURCE_TYPE_ES[e.source_type] ?? e.source_type}</span>{e.publication_date && ` · ${e.publication_date}`}</div>
                        {l.title && <div className="small">{e.source_url ? <a href={e.source_url} target="_blank" rel="noreferrer">{l.title}</a> : l.title}</div>}
                        <div className="small ink2">{e.evidence_excerpt}</div>
                        <div className="small muted">{role} · consultado {e.access_date}{e.reliability_notes ? ` · ${e.reliability_notes}` : ""}</div>
                      </div>
                    );
                  })}</div>
              <div className="step"><div className="k">Evaluación</div>
                <StatusBadge status={c.verification_status} />
                {c.reasoning_summary && <p className="small" style={{ marginTop: 6 }}>{c.reasoning_summary}</p>}
                {c.components_checked && <div className="small muted">Componentes verificados: {c.components_checked}</div>}
                {c.components_unverified && <div className="small muted">Sin verificar: {c.components_unverified}</div>}
                {c.context_flags && <div className="small muted">Contexto: {c.context_flags}</div>}</div>
              <div className="step"><div className="k">Confianza y robustez</div>
                <div className="small">{c.verification_status === "unassessed" ? "—" : `Confianza ${c.confidence ?? "—"} · robustez: ${c.robustness || "—"}`}</div>
                {c.verification_status !== "unassessed" && <div className="small muted">Evaluación preparada por un asistente de IA con las fuentes listadas; pendiente de revisión humana.</div>}</div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
