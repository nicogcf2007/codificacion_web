# Importación empresarial de libros de códigos

## Alcance y ejemplos inspeccionados

Los nueve XLSX de `excel` contienen seis bases y tres libros de códigos. Se inspeccionaron solamente encabezados y estructura de las bases y catálogos de la hoja `Codificación`, sin utilizar respuestas reales ni llamar al proveedor. Los tres libros comparten: `Id campo`, `Cod`, `Label`, `Agrupación`, `# Pregunta del formulario`, `Nombre de la Pregunta`. Hay hojas auxiliares de identificación que no son catálogos y deben ignorarse. Un mismo Id campo puede contener varios identificadores separados por guion, por ejemplo `CP3_1-CP3_2-CP8_1-CP8_2`; el texto de la pregunta aparece generalmente solo en la primera categoría. No asociar por orden ni número de pregunta solamente.

Existen grupos con códigos textuales de uno y tres dígitos; no rellenar, recortar ni renumerar esos valores. Mostrar incompatibilidad por grupo, sin bloquear los otros catálogos válidos. El motor y sus cuatro archivos protegidos no se editan. Su contrato actual acepta exactamente dos dígitos. Hay preguntas de más de 240 caracteres; ampliar solo la validación de texto de pregunta en el adaptador a 2000 caracteres, no truncar.

## Flujo

1. Subir o seleccionar base (.xlsx/.xls/.csv).
2. Seleccionar explícitamente hasta 50 columnas de respuestas.
3. Subir libro de códigos (.xlsx/.xls), separado de la base. Analizar hojas con encabezados reconocidos y mostrar catálogos, categorías y advertencias. La previsualización no crea catálogos ni ejecuciones.
4. Para cada columna elegida, mostrar selector del catálogo. Sugerir solo coincidencias inequívocas del identificador completo o de su contraparte código/respuesta (`CP33T` ↔ `P33T`, `CP27_1NOM` ↔ `P27_1NOM`). No confundir P3 con P33 ni asumir que un guion es un rango. Sin coincidencia o con conflicto, exigir elección manual. Cualquier cambio de base, columnas o archivo invalida la confirmación anterior. Selecciones son propuestas, no confirmación automática.
5. Confirmar correspondencias importa en una sola transacción los catálogos elegidos y atribuye la operación al usuario autenticado. Usar el texto de pregunta del libro; permitir corregirlo antes de preparar. Catálogos guardados siguen disponibles para reutilización explícita. Entrada manual puede quedar como alternativa avanzada, nunca como camino principal obligatorio.
6. Preparar guarda el plan como antes. Iniciar desde monitor sigue separado; no activar proveedor real ni generar llamadas durante upload/import.

## API congelada

Todas las rutas usan sesión/CSRF actuales. No aceptar actor del navegador.

### POST /api/v1/projects/{project_id}/codebooks/preview
Multipart: `file`. Lectura limitada a 50 MB comprimidos / 200 MB descomprimidos, filas y celdas acotadas, cerrar recursos, sin evaluar fórmulas ni seguir enlaces externos. Solo .xlsx/.xls. Ignorar hojas sin encabezados; error 422 si ninguna hoja corresponde. JSON:

```json
{"filename":"libro.xlsx","sheets":["Codificación"],"catalogs":[{"key":"stable-sheet-field-key","sheet":"Codificación","field_id":"CP3_1-CP3_2","question_number":"3","question_text":"Pregunta del libro","categories":[{"code":"01","label":"Categoría"}],"compatible":true,"issues":[],"candidate_columns":["CP3_1","P3_1","CP3_2","P3_2"]}],"warnings":[]}
```

`key` es determinista para hoja/Id campo, se usa de nuevo al importar. `candidate_columns` tiene identificadores completos, no columnas inferidas por posición. Repetidos/conflictos, valores incompatibles, categorías sin etiqueta, fórmulas, errores Excel o pregunta demasiado larga producen `compatible:false` e issues por catálogo; no perder ni reparar códigos textuales. Números integrales pueden representarse como texto; respetar formato explícito `00` sin adivinarlo para formato General. Pregunta vacía es válida en preview y debe completarse en UI antes de preparar.

### POST /api/v1/projects/{project_id}/codebooks/import
Multipart: `file`, `survey_id`, `selections` JSON array:

```json
[{"column_name":"P3_1","catalog_key":"stable-sheet-field-key","max_labels":1}]
```

Volver a analizar el archivo server-side; validar survey/proyecto, 1..50 columnas únicas presentes, catálogo compatible y existente, máximo estricto entero 1..6. No confiar en categorías/texto enviados por navegador. Insertar catálogo una vez por pareja (key,max_labels); compartirlo en las columnas asignadas a esa pareja. Añadir tabla de origen aparte, sin modificar tablas existentes en forma destructiva; guardar filename, sheet, field_id, question_number, question_text, target_columns y Agrupación por categoría cuando exista. Auditoría transaccional `codebook_imported` por catálogo, más `codebook_created` si se necesita compatibilidad histórica. JSON:

```json
{"filename":"libro.xlsx","codebooks":[{"id":"uuid","project_id":"uuid","name":"CP3_1-CP3_2","categories":[{"code":"01","label":"Categoría"}],"max_labels":1,"created_at":"timestamp","source":{"filename":"libro.xlsx","sheet":"Codificación","field_id":"CP3_1-CP3_2","question_number":"3","question_text":"Pregunta del libro","target_columns":["P3_1"],"groupings":{}}}],"mappings":[{"column_name":"P3_1","codebook_id":"uuid","question_text":"Pregunta del libro"}]}
```

GET libros devuelve source opcional (null o ausente para manuales/históricos). Los jobs siguen usando `/coding/jobs` y contrato existente. No insertar origen en data.model_dump() de catálogo manual. Persistir solo catálogos elegidos, no respuestas de ejemplos ni hojas de identificación.

## Verificación

Tests sintéticos XLS/XLSX del formato real, grupos múltiples, pregunta heredada dentro del grupo, reinicio durable, ceros, duplicados/conflictos, códigos 1/001 incompatibles, fórmulas/archivos corruptos/límites, importación atómica, sesión/CSRF/actor y cruce de proyecto. Frontend prueba orden, cargar segundo Excel, opciones propuestas no confirmadas, confirmación obligatoria e invalidación, guardados, error/retry, max_labels, no modelo/API expuestos. Browser con servidor/DB propios y datos sintéticos: base → columnas → libro → confirmar → preparar → demo explícita → exportación. Inspección de compatibilidad real solo catálogos/encabezados, jamás ejecución sobre encuestados reales. No commit, push o despliegue remoto.
