"""Transparent, hand-curated Spanish lexicons used for EXPLORATORY framing
analysis. They are deliberately small and fully listed here so that every
count they produce can be audited and challenged.

Limitations (also in documents/methodology.md):
- Lexicon hits measure word use, not intent, truthfulness or bias.
- Words are context-dependent (e.g. "riesgo" in "gestión del riesgo" is
  technical, not alarmist); counts are not disambiguated.
- Lists were compiled for this project before reading the counts; they were
  not tuned to produce any particular result. Changes must be logged in
  RESEARCH_LOG.md.

Matching is done on lowercased, accent-preserving text with word boundaries.
Multi-word expressions are matched as phrases.
"""

from __future__ import annotations

# Causal markers explicitly required by the project brief (§14).
CAUSAL_MARKERS_CORE = [
    "causó", "provocó", "generó", "produjo", "debido a", "como consecuencia de",
    "resultado de", "gracias a", "por culpa de",
]
# Extended causal markers (plural/other tenses and synonyms). Reported separately.
CAUSAL_MARKERS_EXTENDED = [
    "causaron", "causa de", "a causa de", "provocaron", "generaron", "produjeron",
    "ocasionó", "ocasionaron", "originó", "originaron", "derivó en", "derivaron en",
    "condujo a", "condujeron a", "llevó a", "llevaron a", "se tradujo en", "se tradujeron en",
    "por efecto de", "como resultado de", "a raíz de", "responsable de", "responsables de",
    "lo que ha llevado a", "esto ha generado", "ha generado", "han generado", "ha provocado",
    "han provocado", "ha causado", "han causado",
]

CERTAINTY = [
    "sin duda", "sin lugar a dudas", "indudablemente", "evidentemente", "es evidente",
    "claramente", "definitivamente", "absolutamente", "totalmente", "demuestra", "demuestran",
    "demostró", "comprobado", "comprobada", "confirma", "confirmó", "irrefutable", "inequívoco",
    "inequívoca", "sin precedentes", "siempre", "nunca", "jamás", "en efecto", "es un hecho",
    "está claro", "verificable", "verificables", "rigurosamente", "sistemáticamente",
]

HEDGING = [
    "podría", "podrían", "pudo", "pudieron", "posible", "posiblemente", "probablemente",
    "aparentemente", "al parecer", "presunto", "presunta", "presuntos", "presuntas",
    "presuntamente", "habría", "habrían", "indicios", "eventual", "eventualmente",
    "se estima", "estimado", "estimada", "aproximadamente", "alrededor de", "cerca de",
    "sugiere", "sugieren", "parece", "parecen", "tendría", "tendrían", "riesgo de",
]

MODAL_LEMMAS = ["deber", "poder", "tener que", "haber que", "necesitar", "requerir"]

ATTRIBUTION = [
    "según", "de acuerdo con", "señaló", "señalaron", "indicó", "indicaron", "advirtió",
    "advirtieron", "denunció", "denunciaron", "alertó", "alertaron", "reveló", "revelaron",
    "evidenció", "evidenciaron", "documentó", "documentaron", "constató", "constataron",
    "reportó", "reportaron", "informó", "informaron", "reconoció", "reconocieron",
    "afirmó", "afirmaron", "aseguró", "aseguraron", "estableció", "determinó", "concluyó",
    "encontró", "encontramos", "identificó", "identificaron", "identificamos", "registró",
    "registra", "registraba", "reporta", "evidencia", "advierte",
]

ADVERSARIAL = [
    "gobierno anterior", "régimen anterior", "gobierno saliente", "administración anterior",
    "administración saliente", "funcionarios salientes", "heredamos", "heredado", "heredada",
    "herencia", "recibimos", "desgreño", "altanera", "saqueo", "despilfarro", "sabotaje",
    "obstáculos", "maquillaje", "ocultar", "oculto", "oculta", "negligencia", "complicidad",
    "irresponsable", "irresponsabilidad", "abandono", "improvisación", "captura", "botín",
]

# Thematic frame families (the brief's §11 list: éxito, fracaso, crisis,
# riesgo, crecimiento, seguridad) plus corruption and restoration.
FRAMES = {
    "crisis": ["crisis", "colapso", "colapsó", "emergencia", "quiebra", "bomba", "catástrofe",
               "catastrófico", "caos", "desastre", "hueco", "déficit"],
    "riesgo": ["riesgo", "riesgos", "amenaza", "amenazas", "vulnerable", "vulnerabilidad",
               "peligro", "exposición", "contingente"],
    "fracaso": ["fracaso", "falla", "fallas", "incumplimiento", "incumplió", "ineficiencia",
                "parálisis", "rezago", "baja ejecución", "sin ejecutar", "inejecución",
                "paralizado", "paralizada", "deterioro", "pérdida", "retraso", "retrasos"],
    "corrupcion": ["corrupción", "corrupto", "corruptas", "irregular", "irregulares",
                   "irregularidades", "sobrecosto", "sobrecostos", "detrimento", "desvío",
                   "fraude", "peculado", "soborno", "sin soportes", "sin soporte",
                   "hallazgo fiscal", "hallazgos fiscales", "hallazgos disciplinarios"],
    "exito": ["logro", "logros", "éxito", "exitoso", "avance", "avances", "mejora", "mejoró",
              "cumplimiento", "cumplió", "fortalecimiento", "eficiencia"],
    "crecimiento": ["crecimiento", "creció", "aumento", "aumentó", "incremento", "incrementó",
                    "se duplicó", "se triplicó", "expansión"],
    "seguridad": ["seguridad", "violencia", "grupos armados", "criminal", "criminales",
                  "narcotráfico", "homicidio", "homicidios", "secuestro", "extorsión",
                  "minería ilegal", "economías ilícitas", "control territorial"],
    "restauracion": ["restaurar", "restauración", "reconstrucción", "reconstruir", "rescate",
                     "rescatar", "patria milagro", "orden", "corregir", "corrección", "recuperar",
                     "transformar"],
}

# Small evaluative lexicon (exploratory). Not a sentiment model.
POSITIVE = [
    "logro", "logros", "éxito", "exitoso", "avance", "avances", "mejora", "mejoró", "eficiente",
    "eficiencia", "transparencia", "transparente", "rigor", "riguroso", "honesto", "honestidad",
    "fortalecer", "fortalecimiento", "confianza", "cumplimiento", "calidad", "oportuno",
    "responsable", "legítima", "legítimo", "servicio", "restaurar", "proteger", "garantizar",
]
NEGATIVE = [
    "corrupción", "irregular", "irregulares", "irregularidades", "detrimento", "sobrecosto",
    "sobrecostos", "fraude", "crisis", "colapso", "fracaso", "falla", "fallas", "deterioro",
    "pérdida", "pérdidas", "abandono", "negligencia", "desgreño", "despilfarro", "sabotaje",
    "ineficiencia", "parálisis", "riesgo", "riesgos", "deuda", "deudas", "déficit", "incumplimiento",
    "opacidad", "discrecionalidad", "improvisación", "irresponsable", "grave", "graves", "nocivo",
    "nocivos", "destrucción", "captura", "violencia", "criminal", "ilegal", "indebido", "indebida",
]
