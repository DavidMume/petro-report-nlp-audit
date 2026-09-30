# Limitaciones

Este documento enumera lo que el proyecto **no** puede establecer con los datos y métodos actuales. Se actualiza con cada fase.

## Documento fuente

- La fecha oficial de publicación y la URL original no están confirmadas: el archivo lo entregó directamente el propietario del proyecto. La fecha de creación del PDF (17-ago-2026, exportación de InDesign) no es necesariamente la de publicación.
- Tres páginas (1, 2 y 4) no tienen capa de texto y dos figuras (pp. 14 y 25) son imágenes; su texto se obtuvo por OCR, queda marcado y se excluye del análisis principal. Un bloque de la p. 8 tenía la codificación de caracteres dañada y se releyó con OCR (registrado en `outputs/tables/ocr_repaired_blocks.csv`).
- En la p. 8, la capa de texto omite la "L" de "Ley 951"; el defecto está en el PDF, no en el pipeline.

## NLP

- **Embeddings.** El entorno que generó los resultados publicados bloqueaba huggingface.co, así que no se pudo usar un sentence-transformer multilingüe. Los embeddings son promedios de vectores de palabras estáticos de spaCy `es_core_news_lg`, una representación semántica bastante más débil. BERTopic no se ejecutó. Si se instalan esos paquetes, el código los usa automáticamente, y los resultados cambiarán.
- **Temas.** La coherencia NPMI es baja en todos los modelos y el acuerdo entre modelos es bajo (ARI 0,03–0,11). Los temas dependen del modelo y se presentan solo como descripción.
- **Entidades.** El NER de spaCy en español se equivoca a menudo con este género: fragmentos de nombres de ministerios salen como lugares, y "Estado" o "Gobierno" como entidades. Se aplicaron filtros y correcciones documentadas (`GENERIC_TERMS`, `TYPE_OVERRIDES`), pero la tabla completa de menciones conserva los errores para que se puedan auditar.
- **Lematización.** El lematizador comete errores ocasionales (p. ej., "desatendeír").
- **Sentimiento y marcos.** Los léxicos son pequeños y no distinguen contexto. El clasificador preentrenado se entrenó con reseñas y no concuerda con el léxico (ρ ≈ −0,03). Ninguno mide sesgo, intención ni veracidad.

## Afirmaciones

- La extracción es por reglas y **no tiene revisión humana**. Hay falsos positivos (oraciones sin afirmación verificable) y falsos negativos (afirmaciones sin cifras ni marcadores).
- Tipo sugerido, sujeto-predicado-objeto, fuente citada y cifra principal son heurísticos.
- El recuento de 635 candidatas no es un recuento de afirmaciones del informe.

## Verificación

- Es un **piloto de 10 afirmaciones**, elegidas por su verificabilidad con fuentes públicas y por cubrir varios sectores. No es una muestra aleatoria, así que sus proporciones no describen al informe.
- Varias fuentes primarias (p. ej., el documento original de la Contraloría sobre contratación en enero de 2026) no se consultaron directamente; se usaron notas de prensa que las reproducen, registradas como de origen común.
- Las evaluaciones las preparó un asistente de IA con las fuentes citadas y están **pendientes de revisión humana**.
- Ninguna cifra se reconstruyó todavía desde un dataset bruto (SIIF, SECOP, microdatos GEIH): las reconstrucciones comparan contra publicaciones oficiales o secundarias.
- Coincidir en una cifra no valida la interpretación, la atribución ni el vínculo causal que el informe le da.

## Procedencia lingüística

- No se ejecutó ningún detector de IA: no hay uno validado para español disponible, ni el corpus de calibración (§23.5).
- 61 segmentos es poco para métodos multivariados. Los puntos de cambio dependen mucho del modelo de costo y de la penalización, y ninguno resulta robusto.
- Los cambios de estilo coinciden con cambios de género (cartas, casos, balances firmados por cada ministro), que explican diferencias sin necesidad de suponer procesos de redacción distintos.

## Alcance

- Es una auditoría de un solo documento. No evalúa el desempeño de ningún gobierno.
- El conocimiento del asistente que preparó el piloto llega hasta mediados de 2026. Los hechos posteriores se consultaron en la web el 28-sep-2026 y pueden haberse revisado desde entonces.
