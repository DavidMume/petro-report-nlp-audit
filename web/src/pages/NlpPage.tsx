import { useState } from "react";
import { ChartHead, Heatmap, HBar } from "../components/charts";
import { CHAPTER_ORDER, CHAPTER_SHORT, type DataBundle, fmt } from "../data";

const FRAME_COLS: [string, string][] = [
  ["certainty_per_1k_words", "certeza"], ["hedging_per_1k_words", "atenuación"], ["attribution_per_1k_words", "atribución"],
  ["adversarial_per_1k_words", "adversarial"], ["modal_per_1k_words", "modales"], ["frame_crisis_per_1k_words", "crisis"],
  ["frame_riesgo_per_1k_words", "riesgo"], ["frame_fracaso_per_1k_words", "fracaso"], ["frame_corrupcion_per_1k_words", "corrupción"],
  ["frame_exito_per_1k_words", "éxito"], ["frame_crecimiento_per_1k_words", "crecimiento"], ["frame_seguridad_per_1k_words", "seguridad"],
  ["frame_restauracion_per_1k_words", "restauración"], ["negative_per_1k_words", "léxico neg."], ["positive_per_1k_words", "léxico pos."],
];

export function NlpPage({ d }: { d: DataBundle }) {
  const s = d.meta.stats;
  const [chapter, setChapter] = useState(CHAPTER_ORDER[2]);
  const [ng, setNg] = useState<"bigrams" | "trigrams">("bigrams");
  const tfidf = d.terms.tfidf_by_chapter.filter((r: any) => r.chapter === chapter).slice(0, 12);
  const fbc: Record<string, any> = Object.fromEntries(d.framing.by_chapter.map((r: any) => [r.chapter, r]));
  const chapters = CHAPTER_ORDER.filter((c) => fbc[c]);
  const sent = d.framing.sentiment_by_chapter;
  const causal = d.framing.causal_sentences;
  return (
    <>
      <h1>Lenguaje, términos y marcos</h1>
      <p className="lede">Estadística descriptiva del texto. Nada en esta sección mide veracidad, intención o sesgo.</p>
      <div className="card">
        <table><tbody className="small">
          {[["Oraciones analizadas", fmt(s.sentences)], ["Palabras", fmt(s.words)], ["Longitud media de oración", `${fmt(s.mean_sentence_length_words, 1)} palabras (DE ${fmt(s.sd_sentence_length_words, 1)})`],
            ["Vocabulario (tipos)", fmt(s.vocabulary_word_types)], ["Diversidad léxica (MATTR-500)", fmt(s.mattr_500, 3)],
            ["Hapax legomena", fmt(s.hapax_legomena)], ["Densidad léxica", fmt(s.lexical_density, 3)],
            ["Oraciones con cifras", `${fmt(s.sentences_with_numbers)} (${fmt(100 * s.sentences_with_numbers / s.sentences, 0)}%)`],
            ["Modelo lingüístico", s.spacy_model]].map(([k, v]) => <tr key={k}><th style={{ width: 260 }}>{k}</th><td className="tnum">{v}</td></tr>)}
        </tbody></table>
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <ChartHead title="Términos más frecuentes" sub="Lemas sin palabras vacías; números excluidos." />
          <HBar data={d.terms.top_terms.slice(0, 20)} label="term" value="count" />
        </div>
        <div className="card">
          <ChartHead title="Términos distintivos por capítulo (TF-IDF)" sub="Qué distingue a un capítulo de los demás, no su importancia." />
          <div className="controls"><select value={chapter} onChange={(e) => setChapter(e.target.value)}>
            {CHAPTER_ORDER.map((c) => <option key={c} value={c}>{CHAPTER_SHORT[c]}</option>)}</select></div>
          <HBar data={tfidf} label="term" value="tfidf" fmtValue={(v) => v.toFixed(3)} />
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <ChartHead title="N-gramas más frecuentes" sub="Dentro de cada oración, sobre texto lematizado." />
        <div className="seg" style={{ marginBottom: 8 }}>
          <button className={ng === "bigrams" ? "on" : ""} onClick={() => setNg("bigrams")}>Bigramas</button>
          <button className={ng === "trigrams" ? "on" : ""} onClick={() => setNg("trigrams")}>Trigramas</button>
        </div>
        <HBar data={d.terms[ng].slice(0, 20)} label="ngram" value="count" maxLabel={44} />
      </div>

      <h2>Marcos narrativos y lenguaje evaluativo</h2>
      <p className="small ink2">Ocurrencias por 1.000 palabras de listas de términos transparentes (<code>src/lexicons.py</code>).
        Una palabra como “riesgo” puede ser técnica o alarmista; los conteos no distinguen contexto.</p>
      <div className="card">
        <Heatmap rows={chapters} cols={FRAME_COLS.map((c) => c[0])} rowLabel={(r) => CHAPTER_SHORT[r]}
          colLabel={(c) => FRAME_COLS.find((x) => x[0] === c)![1]} value={(r, c) => Number(fbc[r][c] ?? 0)} />
      </div>

      <h2>Lenguaje causal (revisión especial)</h2>
      <p className="small ink2">Que un indicador cambie durante un gobierno no demuestra que ese gobierno lo causó. Estas{" "}
        {causal.length} oraciones contienen marcadores causales (“debido a”, “generó”, “provocó”…) y quedan marcadas para revisión.</p>
      <div className="card table-wrap">
        <table><thead><tr><th>Pág.</th><th>Marcador</th><th>Oración</th></tr></thead><tbody>
          {causal.map((c: any) => <tr key={c.sentence_id}><td className="num">{c.page}</td>
            <td className="small">{c.marker_core || c.marker_extended}<div className="muted">{c.marker_set === "core" ? "núcleo" : "extendido"}</div></td>
            <td className="small">{c.text}</td></tr>)}
        </tbody></table>
      </div>

      <h2>Sentimiento exploratorio: un resultado negativo</h2>
      <div className="card">
        <p className="small ink2">Comparamos un léxico evaluativo propio con un clasificador preentrenado para español
          (<code>sentiment-analysis-spanish</code>, entrenado con reseñas). Su correlación por oración es{" "}
          <strong>ρ = {fmt(sent[0]?.model_lexicon_spearman, 2)}</strong>: no coinciden. Con un desacuerdo así, ninguna
          puntuación de sentimiento se usa como hallazgo.</p>
        <div className="table-wrap"><table><thead><tr><th>Capítulo</th><th className="num">Oraciones</th><th className="num">Términos pos.</th><th className="num">Términos neg.</th><th className="num">% neg. (léxico)</th><th className="num">Modelo (0–1)</th></tr></thead>
          <tbody>{CHAPTER_ORDER.map((c) => sent.find((r: any) => r.chapter === c)).filter(Boolean).map((r: any) => (
            <tr key={r.chapter}><td>{CHAPTER_SHORT[r.chapter]}</td><td className="num">{r.sentences}</td><td className="num">{r.lexicon_pos}</td>
              <td className="num">{r.lexicon_neg}</td><td className="num">{fmt(100 * r.lexicon_neg_share, 0)}%</td><td className="num">{fmt(r.mean_model_score, 2)}</td></tr>))}
          </tbody></table></div>
      </div>
    </>
  );
}
