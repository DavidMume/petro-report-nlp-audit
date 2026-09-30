# BORRADOR de artículo (no integrado en el portafolio)

> Estado: propuesta preparada por Claude a partir de los resultados del repositorio, para que el autor la reescriba con su voz.
> El `ARTICLE_INTEGRATION_HANDBOOK.md` del portafolio exige integrar el **texto confirmado del autor**, sin reescritura. Por eso este borrador no se integra en `src/data/articles.js`.
> Antes de publicar: revisión humana de las 10 evaluaciones del piloto, verificar cada cifra citada aquí contra `outputs/tables/` y actualizar los números si el pipeline cambia.

---

## Leer el Libro de la Verdad con una hoja de cálculo al lado

*Qué afirma el informe del empalme, cómo lo afirma y qué pasa cuando sus cifras se contrastan con las fuentes*

"El Libro de la Verdad" es un documento de 135 páginas que el Gobierno de Colombia publicó en 2026 como resultado del empalme anticorrupción. Recoge 59 casos agrupados en nueve "comportamientos críticos", 23 hallazgos de corrupción y los balances de 20 sectores de la administración 2022–2026. Un documento así puede leerse de dos maneras: como un veredicto o como un conjunto de afirmaciones que se pueden revisar una por una. Este análisis intenta lo segundo.

La pregunta no es si el informe es verdadero o falso, ni si el gobierno anterior fue bueno o malo. Es más estrecha: qué afirma el documento, cómo construye esas afirmaciones y qué tan bien se sostienen cuando se contrastan con evidencia externa.

### Un documento hecho de cifras

Convertimos el PDF en un corpus en el que cada oración conserva su página y su sección. Resultado: 1.670 oraciones y unas 44.500 palabras analizadas. Casi cuatro de cada diez oraciones contienen una cifra (655 si se cuentan los años), y el vocabulario más frecuente es presupuestal: "millón", "recurso", "billón", "contrato", "ejecución". El informe habla sobre todo en el idioma del presupuesto.

Con reglas simples (montos, porcentajes, fechas, comparaciones, instituciones, atribuciones) identificamos 635 afirmaciones candidatas, 513 de ellas fácticas. Son candidatas: una máquina puede señalar qué oraciones contienen algo verificable, pero no decidir qué es una afirmación ni si es cierta.

### Cómo habla el informe

El tono cambia según el capítulo. Las cartas de presentación y el capítulo final de principios concentran el lenguaje evaluativo ("desgreño", "altanera corrupción"), las referencias al "gobierno saliente" o al "régimen anterior" y el vocabulario de restauración. El capítulo de hallazgos de corrupción es, curiosamente, el más sobrio: tiene la mayor proporción de atribuciones ("según…", "la Contraloría reveló…") y la menor de adjetivos evaluativos.

Esto describe palabras, no intenciones. Contar términos no demuestra sesgo. Muestra dónde el documento argumenta y dónde reporta.

### Diez afirmaciones puestas a prueba

Para una primera prueba elegimos 10 afirmaciones: ocho con cifras contrastables en sectores distintos, una de opinión y una que no se puede verificar con información pública. No es una muestra aleatoria y sus proporciones no describen al informe completo.

Las cifras resistieron bien. La informalidad laboral de 55,7% coincide con el dato anual de 2025 del DANE. Los 521.269 contratos directos por $32,88 billones firmados antes de la Ley de Garantías coinciden con lo que reportó la Contraloría. Los 4.087 kilómetros de Caminos Comunitarios frente a una meta de 33.102 dan exactamente el 12,35% que cita el informe. El recaudo bruto de la DIAN en 2025 difiere en 0,5% del dato oficial.

El patrón que se repite no está en los números, sino en lo que falta alrededor de ellos:

- **La línea base.** Los contratos previos a la Ley de Garantías crecieron 5,2% frente al mismo periodo de 2022; firmar mucho antes de una veda electoral no es nuevo. El informe no lo menciona.
- **El año de comparación.** La caída de la inversión petrolera se mide desde 2014, el último año del auge de precios. Para 2021–2022 la inversión ya rondaba entre 3.100 y 4.400 millones de dólares, así que buena parte de la caída ocurrió antes del gobierno 2022–2026.
- **La métrica.** La UNGRD ejecutó 5,8% de su presupuesto de 2023 si se mide por obligaciones, pero comprometió casi el 100%. Ambas lecturas son correctas; responden preguntas distintas.
- **El tipo de fuente.** Una cifra atribuida a una "investigación" de la revista Cambio proviene de su sección de opinión. Una "auditoría" de la Contraloría sobre la deuda fue, en parte, una advertencia fiscal con seguimiento.

Siete de las ocho afirmaciones fácticas quedaron como "mayormente respaldadas": correctas en lo esencial, pero con contexto que el lector necesita.

### ¿Lo escribió una IA?

El propio informe dice que usó "instrumentos auxiliares de inteligencia artificial" para organizar y procesar información. No dice si la IA redactó texto. El análisis estilométrico no encontró cambios de estilo robustos dentro del documento: las señales más débiles coinciden con el paso de un capítulo a otro, es decir, con cambios de género (cartas, casos, balances firmados por cada ministro). No usamos detectores de IA porque ninguno está calibrado para este tipo de texto en español. Atribuir párrafos a una máquina sin esa calibración sería inventar.

### Qué queda por hacer

Diez afirmaciones son un comienzo, no un balance. Quedan más de 500 candidatas fácticas, reconstrucciones desde los datos brutos (SIIF, SECOP, microdatos del DANE) y una revisión humana de cada evaluación. Todo el proceso es público y reproducible: cada gráfico y cada tabla se regeneran desde el PDF original, y cada afirmación enlaza a su página, su evidencia y su evaluación.

El Libro de la Verdad se presenta como un inventario de hechos. La forma más útil de leerlo es tratar cada hecho como una pregunta: ¿de dónde sale esta cifra, contra qué se compara y qué dejaría de decir si se midiera de otra forma?

---

*Datos, código y metodología: https://github.com/DavidMume/petro-report-nlp-audit · Auditoría interactiva: https://juandamunoz.com/libro-de-la-verdad/*
