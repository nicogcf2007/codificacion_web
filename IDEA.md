# IDEA.md: Plataforma de Codificación Cualitativa con Inteligencia Artificial (CNC)

## 1. Visión General del Proyecto
Esta plataforma es una solución de software empresarial diseñada para el **Centro Nacional de Consultoría (CNC)** y sus clientes corporativos (como Mibanco, entidades gubernamentales y firmas de investigación de mercados). 

Su propósito central es **automatizar y acelerar el proceso de codificación cualitativa de respuestas abiertas en encuestas masivas**, transformando texto libre expresado en lenguaje natural por miles de encuestados en **categorías y códigos numéricos estandarizados** según los libros de códigos (*codebooks*) oficiales de cada estudio.

---

## 2. El Problema de Negocio que Resuelve
En la investigación de mercados y opinión pública, las preguntas abiertas (ej. *"¿Por qué cambiaría de banco?"*, *"¿Qué comodidades le gustaría ver en el aeropuerto?"*) capturan los matices más valiosos del encuestado, pero procesarlas tradicionalmente requería:
- **Semanas de trabajo manual:** Equipos humanos leyendo línea por línea miles de respuestas en hojas de cálculo.
- **Altos costos operativos:** Facturación masiva de horas-hombre de digitadores y codificadores.
- **Inconsistencia humana:** Sesgos cognitivos, fatiga y discrepancias de criterio entre codificadores distintos ante respuestas ambiguas o solapadas.
- **Riesgo en LLMs tradicionales:** Si se envía cada texto individual a un modelo grande (como GPT-4o clásico), los costos de API se disparan y las alucinaciones o la falta de rigor metodológico comprometen los resultados del estudio.

---

## 3. La Solución Tecnológica: Arquitectura del Motor
La plataforma resuelve este problema combinando **ciencia de datos algorítmica** con **modelos de lenguaje de última generación altamente calibrados**:

### Flujo Metodológico Central:
1. **Carga Inteligente de Insumos:**
   - **Archivo de Respuestas:** Archivo Excel con columnas de texto abierto de los encuestados.
   - **Libro de Códigos (*Codebook*):** Archivo Excel con la taxonomía oficial de categorías (`Cod` y `Label`), admitiendo preguntas de código único o multicódigo (`CP3_1`, `CP3_2`, `CP3_3`, etc.).
2. **Pre-limpieza y Filtrado Inmediato:**
   - Textos vacíos, signos de puntuación aislados (`.`, `-`, `?`, `/`) o ruido ininteligible son pre-clasificados directamente como código `99` (No sabe / No responde) a costo computacional cero.
3. **Pre-agrupamiento Difuso (*Fuzzy Clustering* al 85%):**
   - Antes de llamar a la IA, un algoritmo de similitud difusa (`rapidfuzz`) agrupa frases idénticas o fuertemente sinónimas alrededor de un texto prototipo.
   - **Impacto probado:** Ahorra el **72.3% de las llamadas a la API** manteniendo una pureza temática del **73.66%**, reduciendo el costo de codificar 10,000 registros a menos de \$0.10 USD.
4. **Inferencia con GPT-6-Luna (Sin Razonamiento + Determinismo Puro):**
   - Solo los prototipos únicos son enviados al modelo `gpt-6-luna` configurado con `reasoning_effort="none"` y `temperature=0.0`.
   - Utiliza un **English Methodological System Prompt** especialmente diseñado con el **Principio de Parsimonia**, reglas de desempate temático (crédito vs agilidad general, requisitos vs papeleo) y distinción estricta de fidelidad (`88`) vs desconocimiento (`99`).
   - La respuesta del modelo se obtiene en apenas **1.0 segundo** en formato directo de números de dos dígitos separados por punto y coma (ej. `01` o `01;05`).
5. **Propagación y Mapeo Inverso:**
   - El código generado por la IA para el prototipo se replica instantáneamente a todos los miembros de su clúster.
6. **Cola de Revisión Humana (*Human-in-the-Loop*):**
   - Respuestas atípicas que no encajan en el catálogo (asignadas a código `77` - Otro) o casos de baja confianza se envían a un buzón de triage para que un metodólogo humano decida si aprobarlas o crear una categoría nueva en lote.
7. **Exportación Estándar CNC:**
   - Generación del archivo Excel final con la matriz de datos original complementada con las columnas de códigos codificadas según la convención técnica del CNC.

---

## 4. Usuarios Objetivos
1. **Analistas Cualitativos y Metodólogos del CNC:** Crean y calibran los libros de códigos, validan casos atípicos y aprueban la coherencia temática.
2. **Líderes de Operaciones y Procesamiento de Datos:** Ejecutan las codificaciones de encuestas masivas (desde cientos hasta cientos de miles de registros) y descargan los entregables finales.
3. **Gerentes de Proyecto / Clientes Corporativos:** Consultan dashboards de avance, métricas de distribución de categorías y análisis de sentimientos o satisfacción.

---

## 5. Hacia Dónde Evoluciona la Nueva Versión
El proyecto actualmente cuenta con su motor central completamente validado y optimizado, pero requiere una **reinversión total de la experiencia de usuario y arquitectura de software**:
- **Nueva Interfaz UI/UX:** Diseño moderno, limpio, responsivo y profesional (Dark/Light mode, componentes Shadcn/UI, feedback visual interactivo y micro-interacciones).
- **Gestión Persistente de Proyectos:** Pasar de sesiones efímeras a un esquema de base de datos relacional (listo para PostgreSQL / Supabase / SQLite) para organizar estudios por cliente, versiones de encuestas y trazabilidad histórica.
- **Resiliencia de Ejecución (Pausa y Reanudación):** Si durante un proceso masivo la cuenta se queda sin saldo o hay un corte de red, el sistema congela el progreso sin perder datos ni duplicar costos, permitiendo reanudar con un solo clic una vez restablecido el servicio.
- **Monitor en Tiempo Real:** Visualización en vivo mediante WebSockets de la velocidad (registros/seg), costo financiero acumulado y ahorro en dólares respecto a métodos convencionales.
