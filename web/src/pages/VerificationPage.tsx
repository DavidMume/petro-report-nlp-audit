import { ChartHead, HBar, StatusBadge } from "../components/charts";
import { type DataBundle, fmt, SOURCE_TYPE_ES, STATUS_ES, STATUS_ORDER, STATUS_VAR, TYPE_ES } from "../data";
import { readVar } from "../theme";

export function VerificationPage({ d, openClaim }: { d: DataBundle; openClaim: (id: string) => void }) {
  const assessed = d.claims.filter((c) => c.verification_status !== "unassessed");
  const cov = Object.fromEntries(d.meta.coverage.map((r: any) => [r.metric, r.value]));
  const dist = STATUS_ORDER.filter((s) => s !== "unassessed").map((s) => ({ status: STATUS_ES[s], key: s, n: assessed.filter((c) => c.verification_status === s).length }));
  const recon = d.numeric.reconstructions;
  return (
    <>
      <h1>Verificación</h1>
      <p className="lede">Las afirmaciones se contrastan con evidencia externa explícita, priorizando fuentes oficiales. No
        se usa una escala verdadero/falso, y ninguna evaluación sale solo del juicio de un modelo: cada una cita sus fuentes.</p>
      <div className="note">
        <strong>Piloto, no muestra.</strong> Se evaluaron {assessed.length} afirmaciones de {fmt(cov.factual_candidates)} fácticas
        candidatas ({fmt(cov.assessed_share_of_factual_candidates_pct, 1)}%), elegidas por tener cifras contrastables con fuentes
        públicas y por cubrir distintos sectores, más dos ejemplos de las categorías no fácticas. Los porcentajes de este
        piloto no describen al informe completo. Las evaluaciones las preparó un asistente de IA con las fuentes listadas y
        están pendientes de revisión humana.
      </div>
      <div className="grid grid-2">
        <div className="card">
          <ChartHead title="Estado de verificación del piloto" sub={`${fmt(d.claims.length - assessed.length)} candidatas siguen sin evaluar.`} />
          <HBar data={dist} label="status" value="n" colorOf={(r) => readVar(STATUS_VAR[r.key])} maxLabel={36} />
        </div>
        <div className="card">
          <ChartHead title="Reconstrucción de cifras" sub="Valor del informe frente a la fuente independiente. Coincidir en la cifra no valida la interpretación." />
          <div className="table-wrap"><table><thead><tr><th>ID</th><th>Variable</th><th className="num">Informe</th><th className="num">Fuente</th><th className="num">Dif. %</th></tr></thead>
            <tbody>{recon.map((r: any, i: number) => <tr key={i}><td><a href="#" onClick={(e) => { e.preventDefault(); openClaim(r.claim_id); }}>{r.claim_id}</a></td>
              <td className="small">{r.variable}<div className="muted">{r.independent_dataset}</div></td>
              <td className="num">{r.reported_value} {r.reported_unit}</td><td className="num">{r.reconstructed_value}</td>
              <td className="num">{r.difference_percent > 0 ? "+" : ""}{fmt(r.difference_percent, 2)}</td></tr>)}</tbody></table></div>
        </div>
      </div>

      <h2>Matriz de verificación</h2>
      <div className="card table-wrap">
        <table><thead><tr><th>ID</th><th>Pág.</th><th>Tipo</th><th>Afirmación</th><th>Evaluación</th><th>Por qué</th><th>Robustez</th></tr></thead>
          <tbody>{assessed.map((c) => (
            <tr key={c.claim_id}>
              <td><a href="#" onClick={(e) => { e.preventDefault(); openClaim(c.claim_id); }}>{c.claim_id}</a></td>
              <td className="num">{c.page}</td><td className="small">{TYPE_ES[c.claim_type]}</td>
              <td className="small" style={{ minWidth: 240 }}>{c.short_quote}</td>
              <td><StatusBadge status={c.verification_status} /><div className="small muted">confianza {c.confidence}</div></td>
              <td className="small" style={{ minWidth: 280 }}>{c.reasoning_summary}</td>
              <td className="small">{c.robustness || "—"}</td>
            </tr>))}</tbody></table>
      </div>

      <h2>Triangulación de fuentes</h2>
      <p className="small ink2">Tres artículos que reproducen el mismo dato de la Contraloría no son tres evidencias
        independientes. Registramos el origen común.</p>
      <div className="card table-wrap"><table><thead><tr><th>ID</th><th>Variable</th><th>Fuente A</th><th>Fuente B</th><th>Fuente C</th><th>Origen común</th></tr></thead>
        <tbody>{d.numeric.triangulation.map((t: any, i: number) => <tr key={i}><td>{t.claim_id}</td><td className="small">{t.variable}</td>
          <td className="small">{t.source_a}: <strong>{t.source_a_value}</strong></td><td className="small">{t.source_b}: <strong>{t.source_b_value}</strong></td>
          <td className="small">{t.source_c ? <>{t.source_c}: <strong>{t.source_c_value}</strong></> : "—"}</td><td className="small">{t.common_origin}<div className="muted">{t.notes}</div></td></tr>)}</tbody></table></div>

      <h2>Categorías de evaluación</h2>
      <div className="card"><ul className="small">
        {[["supported", "la evidencia disponible respalda sustancialmente la afirmación."], ["mostly_supported", "correcta en lo esencial, pero requiere contexto."],
          ["mixed_or_disputed", "hay elementos ciertos y otros discutibles."], ["misleading_without_context", "los datos pueden ser correctos, pero su interpretación requiere información omitida."],
          ["unsupported", "no se encontró evidencia suficiente."], ["contradicted", "evidencia confiable contradice la afirmación."],
          ["not_independently_verifiable", "no puede comprobarse razonablemente con información pública."], ["opinion_or_interpretation", "no corresponde tratarla como afirmación fáctica."]]
          .map(([k, v]) => <li key={k}><StatusBadge status={k} /> {v}</li>)}
      </ul>
        <p className="small muted">Jerarquía de evidencia: dataset oficial → publicación estadística oficial → documento oficial →
          investigación arbitrada → organismo multilateral → investigación independiente → periodismo → opinión → redes sociales.
          Que una fuente sea oficial no la hace correcta automáticamente. Tipos usados aquí: {Object.entries(
            d.ledger.reduce((m: any, l: any) => ((m[l.source_type] = (m[l.source_type] || 0) + 1), m), {}))
            .map(([k, v]) => `${SOURCE_TYPE_ES[k] ?? k} (${v})`).join(", ")}.</p></div>
    </>
  );
}
