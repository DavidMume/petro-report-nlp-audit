import { useEffect, useState } from "react";

// All data comes from web/public/data/*.json, produced by scripts/export_web_data.py.
// The web app computes nothing analytical on its own.

export type Row = Record<string, any>;

export interface Claim {
  claim_id: string; claim_text: string; short_quote: string; page: number; section: string; chapter: string;
  level2: string; claim_type: string; claim_kind: string; priority: string; extraction_score: number; cues: string;
  is_causal: boolean; time_period: string | null; numeric_value: number | null; unit: string | null;
  source_cited_in_report: string | null; verifiable: string; verification_status: string; confidence: string | null;
  reasoning_summary: string | null; robustness: string | null; context_flags: string | null;
  components_checked: string | null; components_unverified: string | null; evidence_source_ids: string | null;
  paragraph_id: string; sentence_id: string; subject: string | null; predicate: string | null; object: string | null;
}

export interface Paragraph {
  paragraph_id: string; page: number; page_end: number; section: string; chapter: string; level2: string;
  level3: string; block_type: string; is_ocr: boolean; clean_text: string; n_words: number;
}

export interface DataBundle {
  meta: Row; paragraphs: Paragraph[]; sections: Row[]; wordsPerPage: Row[]; claims: Claim[]; evidence: Row[];
  ledger: Row[]; numeric: { reconstructions: Row[]; triangulation: Row[] }; entities: Row[];
  entityNetwork: Row; conceptNetwork: Row; terms: Row; topics: Row; embeddingMap: Row[]; framing: Row;
  stylometry: Row; methodology: { markdown: string; limitations: string };
}

const FILES: Record<keyof DataBundle, string> = {
  meta: "meta.json", paragraphs: "paragraphs.json", sections: "sections.json", wordsPerPage: "words_per_page.json",
  claims: "claims.json", evidence: "evidence.json", ledger: "ledger.json", numeric: "numeric.json",
  entities: "entities.json", entityNetwork: "entity_network.json", conceptNetwork: "concept_network.json",
  terms: "terms.json", topics: "topics.json", embeddingMap: "embedding_map.json", framing: "framing.json",
  stylometry: "stylometry.json", methodology: "methodology.json",
};

export function useData(): { data: DataBundle | null; error: string | null } {
  const [data, setData] = useState<DataBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const base = import.meta.env.BASE_URL + "data/";
    Promise.all(
      Object.entries(FILES).map(async ([k, f]) => {
        const r = await fetch(base + f);
        if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`);
        return [k, await r.json()] as const;
      }),
    )
      .then((pairs) => setData(Object.fromEntries(pairs) as unknown as DataBundle))
      .catch((e) => setError(String(e)));
  }, []);
  return { data, error };
}

export const CHAPTER_ORDER = [
  "0. Preliminares",
  "I. Proceso metodológico del empalme",
  "II. Comportamientos críticos nocivos para el Estado",
  "III. Hallazgos en materia de corrupción y balance de acciones",
  "IV. Balance sectorial",
  "V. Principios de Gobierno de la Patria Milagro",
];
export const CHAPTER_SHORT: Record<string, string> = {
  "0. Preliminares": "0 · Preliminares",
  "I. Proceso metodológico del empalme": "I · Metodología",
  "II. Comportamientos críticos nocivos para el Estado": "II · Comportamientos",
  "III. Hallazgos en materia de corrupción y balance de acciones": "III · Corrupción",
  "IV. Balance sectorial": "IV · Balance sectorial",
  "V. Principios de Gobierno de la Patria Milagro": "V · Principios",
};
export const CHAPTER_VAR = ["--series-1", "--series-2", "--series-3", "--series-4", "--series-5", "--series-6"];

export const STATUS_ORDER = [
  "supported", "mostly_supported", "mixed_or_disputed", "misleading_without_context", "unsupported", "contradicted",
  "not_independently_verifiable", "opinion_or_interpretation", "unassessed",
];
export const STATUS_ES: Record<string, string> = {
  supported: "Respaldada", mostly_supported: "Mayormente respaldada", mixed_or_disputed: "Mixta / disputada",
  misleading_without_context: "Engañosa sin contexto", unsupported: "Sin respaldo", contradicted: "Contradicha",
  not_independently_verifiable: "No verificable independientemente", opinion_or_interpretation: "Opinión / interpretación",
  unassessed: "Sin evaluar",
};
export const STATUS_VAR: Record<string, string> = {
  supported: "--st-supported", mostly_supported: "--st-mostly", mixed_or_disputed: "--st-mixed",
  misleading_without_context: "--st-misleading", unsupported: "--st-unsupported", contradicted: "--st-contradicted",
  not_independently_verifiable: "--st-niv", opinion_or_interpretation: "--st-opinion", unassessed: "--st-unassessed",
};
export const TYPE_ES: Record<string, string> = {
  economico: "Económico", fiscal: "Fiscal", empleo: "Empleo", seguridad: "Seguridad", salud: "Salud",
  energia: "Energía", instituciones: "Instituciones", corrupcion: "Corrupción", politica_social: "Política social",
  infraestructura: "Infraestructura", relaciones_internacionales: "Relaciones internacionales", otros: "Otros",
};
export const SOURCE_TYPE_ES: Record<string, string> = {
  raw_official_dataset: "Dataset oficial", official_statistical_publication: "Publicación estadística oficial",
  legislation_or_official_document: "Documento oficial", peer_reviewed_research: "Investigación arbitrada",
  multilateral_organisation: "Organismo multilateral", independent_research: "Investigación independiente",
  reputable_journalism: "Periodismo", commentary: "Opinión / columna", social_media: "Redes sociales",
  audited_document: "Documento auditado", coverage_of_audited_document: "Cobertura del informe (no evidencia)",
};

export const REPO_URL = "https://github.com/DavidMume/petro-report-nlp-audit";

export const fmt = (n: number | null | undefined, d = 0) =>
  n === null || n === undefined || Number.isNaN(n) ? "—" : n.toLocaleString("es-CO", { maximumFractionDigits: d, minimumFractionDigits: d });
