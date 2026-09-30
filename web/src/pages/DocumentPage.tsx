import { useMemo, useState } from "react";
import { CHAPTER_ORDER, CHAPTER_SHORT, type DataBundle, fmt } from "../data";

export function DocumentPage({ d }: { d: DataBundle }) {
  const m = d.meta.source;
  const [chapter, setChapter] = useState(CHAPTER_ORDER[1]);
  const secs = d.sections.filter((s: any) => s.chapter === chapter);
  const [sec, setSec] = useState<string | null>(null);
  const paras = useMemo(
    () => d.paragraphs.filter((p) => p.chapter === chapter && (!sec || p.level2 === sec) && p.block_type !== "running_title"),
    [d, chapter, sec],
  );
  return (
    <>
      <h1>Documento y procedencia</h1>
      <p className="lede">El archivo original se conserva sin modificar en <code>data/raw/</code>; cada resultado del análisis
        se puede rastrear hasta una página de ese archivo.</p>
      <div className="grid grid-2">
        <div className="card">
          <h3>Metadatos verificados</h3>
          <table><tbody>
            {[["Título", m.title], ["Subtítulo", m.subtitle], ["Editor", m.publisher], ["Páginas", m.pages],
              ["Archivo", m.filename], ["SHA-256", <span className="mono" key="h" style={{ wordBreak: "break-all" }}>{m.sha256}</span>],
              ["Creación del PDF (InDesign)", m.pdf_creation_date], ["Fecha de publicación oficial", m.publication_date ?? "no confirmada"],
              ["URL original", m.original_url ?? "no confirmada (archivo entregado directamente)"], ["Fecha de incorporación", m.download_date]]
              .map(([k, v]) => <tr key={String(k)}><th style={{ width: 190 }}>{k}</th><td>{v as any}</td></tr>)}
          </tbody></table>
        </div>
        <div className="card">
          <h3>Firmantes y autoría declarada</h3>
          <ul className="small">{m.authors.map((a: string) => <li key={a}>{a}</li>)}</ul>
          <p className="small muted">Transcrito de la portada, el índice y las cartas de presentación (pp. 1, 3, 5, 7). La
            sigla “ADLA” no se usa en este proyecto: el documento no la emplea para identificar al autor.</p>
          <h3>Extracción</h3>
          <p className="small ink2">PyMuPDF para {fmt(d.meta.extraction.pymupdf_pages)} páginas con capa de texto; OCR
            (Tesseract, español) solo para {fmt(d.meta.extraction.ocr_pages)} páginas sin texto (pp.{" "}
            {d.meta.extraction.ocr_page_numbers.join(", ")}) y para las figuras rasterizadas de las pp.{" "}
            {d.meta.extraction.figure_ocr_pages.join(" y ")}. El texto OCR queda marcado y excluido del análisis principal.
            Se eliminaron {fmt(d.meta.extraction.removed_header_footer_lines)} líneas de encabezado/pie repetidas (registradas
            en <code>removed_headers_footers.csv</code>).</p>
        </div>
      </div>

      <h2>Navegador del documento</h2>
      <div className="controls">
        <select value={chapter} onChange={(e) => { setChapter(e.target.value); setSec(null); }}>
          {CHAPTER_ORDER.map((c) => <option key={c} value={c}>{CHAPTER_SHORT[c]}</option>)}
        </select>
        <select value={sec ?? ""} onChange={(e) => setSec(e.target.value || null)}>
          <option value="">Todas las secciones ({secs.length})</option>
          {secs.map((s: any) => <option key={s.level2} value={s.level2}>{s.level2} · pp. {s.page_start}–{s.page_end}</option>)}
        </select>
        <span className="small muted">{paras.length} bloques</span>
      </div>
      <div className="card" style={{ maxHeight: "70vh", overflowY: "auto" }}>
        {paras.map((p) => (
          <div key={p.paragraph_id} style={{ marginBottom: 12 }}>
            <div className="small muted mono">{p.paragraph_id} · p. {p.page}{p.page_end !== p.page ? `–${p.page_end}` : ""} · {p.block_type}{p.is_ocr ? " · OCR" : ""}</div>
            {p.block_type === "heading" ? <strong>{p.clean_text}</strong> : <p style={{ maxWidth: "none" }}>{p.clean_text}</p>}
          </div>
        ))}
      </div>
    </>
  );
}
