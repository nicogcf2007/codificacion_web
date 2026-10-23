import { useEffect, useRef, useState } from "react";
import { ArrowRight, Check } from "lucide-react";
import { api, message } from "./api";
import { Upload } from "./Upload";
import { suggestCatalog } from "./codebookMapping";
import type { Project, Survey, Codebook, CodebookPreview, CodebookImport, Category, Job } from "./types";

interface QuestionDraft {
  column_name: string;
  question_text: string;
  codebook_id: string;
  catalog_key: string;
  max_labels: number;
}
interface ComposerProps {
  project: Project;
  onCreated: (job: Job) => void;
  report: (error: string) => void;
}
function Categories({ categories }: { categories: Category[] }) {
  return <div className="category-preview">{categories.map((category, index) =>
    <div key={`${category.code}-${index}`}><code>{category.code}</code><span>{category.label}</span></div>)}</div>;
}
export function Composer(props: ComposerProps) {
  return <ComposerForm key={props.project.id} {...props} />;
}
function ComposerForm({ project, onCreated, report }: ComposerProps) {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [books, setBooks] = useState<Codebook[]>([]);
  const [surveyId, setSurveyId] = useState("");
  const [questions, setQuestions] = useState<QuestionDraft[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CodebookPreview | null>(null);
  const [usingSaved, setUsingSaved] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [jobName, setJobName] = useState(project.name);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const reportRef = useRef(report);
  reportRef.current = report;
  const survey = surveys.find((item) => item.id === surveyId);
  useEffect(() => {
    let current = true;
    void Promise.all([
      api.request<{ surveys: Survey[] }>(`/projects/${project.id}/surveys`),
      api.request<{ codebooks: Codebook[] }>(`/projects/${project.id}/codebooks`),
    ]).then(([bases, catalogs]) => {
      if (current) { setSurveys(bases.surveys); setBooks(catalogs.codebooks); }
    }).catch((problem) => { if (current) reportRef.current(message(problem)); });
    return () => { current = false; };
  }, [project.id]);
  const selectSurvey = (id: string) => {
    setSurveyId(id); setQuestions([]); setConfirmed(false); setFile(null); setPreview(null); setUsingSaved(false); setError("");
  };
  const selectColumn = (column: string, checked: boolean) => {
    setConfirmed(false);
    setQuestions((previous) => checked ? [...previous, { column_name: column, question_text: "", codebook_id: "", catalog_key: usingSaved ? "" : suggestCatalog(column, preview?.catalogs || []), max_labels: 1 }] : previous.filter((question) => question.column_name !== column));
  };
  const chooseCatalog = (column: string, key: string) => {
    setConfirmed(false); setError("");
    setQuestions((previous) => previous.map((question) => question.column_name === column ? { ...question, catalog_key: key, codebook_id: usingSaved ? key : "", question_text: "" } : question));
  };
  const canConfirm = usingSaved
    ? (!busy && questions.length > 0 && questions.every((q) => !!q.catalog_key))
    : (!!survey && !!file && !!preview && questions.length > 0 && questions.every((question) => preview.catalogs.some((catalog) => catalog.key === question.catalog_key && catalog.compatible)));
  const ready = confirmed && !!survey && !!jobName.trim() && questions.every((question) => question.codebook_id && question.question_text.trim() && question.question_text.length <= 2000);
  const confirm = async () => {
    if (!canConfirm || busy) return;
    if (usingSaved) {
      setQuestions((previous) =>
        previous.map((question) => {
          const book = books.find((b) => b.id === question.catalog_key);
          return {
            ...question,
            codebook_id: book?.id || "",
            question_text: book?.source?.question_text || "",
          };
        })
      );
      setConfirmed(true);
      return;
    }
    if (!file) return;
    setBusy("confirm"); setError("");
    try {
      const body = new FormData();
      body.append("file", file); body.append("survey_id", surveyId);
      body.append("selections", JSON.stringify(questions.map((question) => ({ column_name: question.column_name, catalog_key: question.catalog_key, max_labels: question.max_labels }))));
      const imported = await api.request<CodebookImport>(`/projects/${project.id}/codebooks/import`, { method: "POST", body });
      if (questions.some((question) => !imported.mappings.some((mapping) => mapping.column_name === question.column_name && imported.codebooks.some((book) => book.id === mapping.codebook_id)))) throw new Error("No se recibieron todas las correspondencias. Vuelve a confirmarlas.");
      setBooks((previous) => [...imported.codebooks, ...previous.filter((book) => !imported.codebooks.some((item) => item.id === book.id))]);
      setQuestions((previous) => previous.map((question) => ({ ...question, ...imported.mappings.find((mapping) => mapping.column_name === question.column_name)! })));
      setConfirmed(true);
    } catch (problem) { setError(message(problem)); }
    finally { setBusy(""); }
  };
  const prepare = async () => {
    if (!ready || busy) return;
    setBusy("job"); setError("");
    try {
      const job = await api.post<Job>("/coding/jobs", { survey_id: surveyId, name: jobName, questions: questions.map(({ column_name, question_text, codebook_id }) => ({ column_name, question_text, codebook_id })) });
      onCreated(job);
    } catch (problem) { setError(message(problem)); }
    finally { setBusy(""); }
  };
  return <div className="compose-layout excel-composer">
    <div className="workflow-ribbon" aria-label="Pasos de preparación">
      <span className={survey ? "done" : ""}>{survey ? <Check size={14} /> : "1"} 1. Base</span><i />
      <span className={questions.length ? "done" : ""}>{questions.length ? <Check size={14} /> : "2"} 2. Columnas</span><i />
      <span className={preview || usingSaved ? "done" : ""}>{preview || usingSaved ? <Check size={14} /> : "3"} 3. Libro Excel</span><i />
      <span className={confirmed ? "done" : ""}>{confirmed ? <Check size={14} /> : "4"} 4. Confirmar</span><i />
      <span>5. Preparar</span>
    </div>
    <div className="compose-grid">
      <section className="panel form-stack" aria-label="Base de respuestas">
        <div>
          <span className="eyebrow">01 · ARCHIVO DE LA ENCUESTA</span>
          <h2>Base de respuestas</h2>
          <p className="muted">Sube el archivo Excel o CSV con las respuestas recogidas en la encuesta o selecciona una base guardada.</p>
        </div>
        <div className="helper-box">
          <strong>💡 Ejemplo de base de respuestas:</strong>
          <p>Es la tabla con las respuestas de campo, donde cada fila es una persona encuestada y las columnas contienen sus respuestas (ej. <code>ID</code>, <code>P1</code>, <code>P59_1</code>, <code>P33</code>).</p>
        </div>
        <Upload disabled={!!busy} onUpload={async (uploadedFile) => {
          setBusy("base");
          try {
            const body = new FormData(); body.append("file", uploadedFile);
            const uploaded = await api.request<Survey>(`/projects/${project.id}/surveys`, { method: "POST", body });
            setSurveys((previous) => [uploaded, ...previous.filter((item) => item.id !== uploaded.id)]); selectSurvey(uploaded.id);
          } finally { setBusy(""); }
        }} />
        <label>O usar una base guardada<select value={surveyId} onChange={(event) => selectSurvey(event.target.value)}>
          <option value="">Selecciona una base</option>{surveys.map((item) => <option key={item.id} value={item.id}>{item.filename} · {item.total_records} registros</option>)}
        </select></label>
        {survey && <div className="file-summary"><strong>{survey.filename}</strong><span>{survey.total_records} registros · {survey.columns.length} columnas</span></div>}
      </section>
      <section className="panel form-stack" aria-label="Seleccionar columnas">
        <div>
          <span className="eyebrow">02 · PREGUNTAS A CODIFICAR</span>
          <h2>Seleccionar columnas</h2>
          <p className="muted">Elige las columnas de la encuesta que tienen texto abierto para clasificar.</p>
        </div>
        <div className="helper-box">
          <strong>💡 Ejemplo de selección:</strong>
          <p>Marca preguntas abiertas como <code>P59_1</code> (<i>"¿Por qué motivo prefiere el servicio?"</i>) o <code>P33</code> (<i>"¿Qué mejoras sugiere?"</i>). No es necesario marcar preguntas cerradas de Sí/No ni identificadores numéricos.</p>
        </div>
        {!survey ? <p className="muted">Selecciona una base para ver sus columnas.</p> : <>
          <p className="muted">{questions.length} columnas seleccionadas</p>
          <div className="column-picker">{survey.columns.map((column) => {
            const checked = questions.some((question) => question.column_name === column);
            return <label key={column} className={`column-option ${checked ? "selected" : ""}`}><input type="checkbox" checked={checked} onChange={(event) => selectColumn(column, event.target.checked)} /><code>{column}</code></label>;
          })}</div>
        </>}
      </section>
    </div>
    <section className="panel form-stack" aria-label="Libro de códigos">
      <div>
        <span className="eyebrow">03 · DICCIONARIO DE TEMAS</span>
        <h2>Libro de códigos</h2>
        <p className="muted">Este Excel es distinto de la base: contiene las preguntas y sus categorías oficiales.</p>
      </div>
      <div className="helper-box">
        <strong>💡 ¿Qué es el libro de códigos?</strong>
        <p>Es el documento oficial donde se definen los códigos numéricos y sus descripciones temáticas (ej. <code>01 = Atención rápida</code>, <code>02 = Precios bajos</code>, <code>88 = Nada / Ninguna</code>, <code>99 = No sabe / No responde</code>).</p>
      </div>
      <Upload key={surveyId} kind="codebook" disabled={!survey || !questions.length || !!busy} onUpload={async (uploadedFile) => {
        setBusy("preview"); setConfirmed(false); setPreview(null); setFile(null); setUsingSaved(false); setError("");
        try {
          const body = new FormData(); body.append("file", uploadedFile);
          const parsed = await api.request<CodebookPreview>(`/projects/${project.id}/codebooks/preview`, { method: "POST", body });
          setFile(uploadedFile); setPreview(parsed);
          setQuestions((previous) => previous.map((question) => ({ ...question, catalog_key: suggestCatalog(question.column_name, parsed.catalogs), codebook_id: "", question_text: "" })));
        } finally { setBusy(""); }
      }} />
      {books.length > 0 && (
        <div className="row wrap" style={{ gap: "10px", alignItems: "center" }}>
          <button
            type="button"
            className="button secondary"
            disabled={!survey || !questions.length || !!busy}
            onClick={() => {
              setUsingSaved(true);
              setPreview(null);
              setFile(null);
              setConfirmed(false);
              setQuestions((previous) =>
                previous.map((q) => ({ ...q, catalog_key: "", codebook_id: "", question_text: "" }))
              );
            }}
          >
            Reutilizar catálogos guardados
          </button>
          <small className="muted">({books.length} catálogos ya cargados en este proyecto)</small>
        </div>
      )}
      {!questions.length && <p className="muted">Selecciona primero las columnas de respuestas.</p>}
      {preview && <div className="codebook-preview">
        <p className="muted">{preview.filename} · Hojas reconocidas: {preview.sheets.join(", ")} · {preview.catalogs.length} catálogos. La previsualización no guarda catálogos.</p>
        {preview.warnings.map((warning, index) => <p key={index} className="notice warning">{warning}</p>)}
        {preview.catalogs.map((catalog) => <details className="catalog-card" key={catalog.key}>
          <summary><strong>{catalog.field_id}</strong><span className="muted">{catalog.sheet} · {catalog.categories.length} categorías</span><span className={catalog.compatible ? "chip" : "field-error"}>{catalog.compatible ? "Compatible" : "No compatible"}</span></summary>
          <div className="catalog-content"><p>{catalog.question_text || "Sin texto de pregunta: complétalo antes de preparar."}</p>{catalog.issues.map((issue, index) => <p className="field-error" key={index}>{issue}</p>)}<Categories categories={catalog.categories} /></div>
        </details>)}
      </div>}
    </section>
    <section className="panel form-stack" aria-label="Confirmar correspondencias">
      <div>
        <span className="eyebrow">04 · CORRESPONDENCIAS Y LÍMITES POR PREGUNTA</span>
        <h2>Confirmar correspondencias</h2>
        <p className="muted">Asigna a cada pregunta su catálogo de códigos y define cuántos códigos como máximo se pueden asignar por respuesta.</p>
      </div>
      <div className="helper-box">
        <div>
          <strong>💡 ¿Qué son las "Correspondencias"?</strong>
          <p>
            Es la relación entre la pregunta de tu encuesta (ej. <code>P59_1</code>) y la lista de códigos del Excel que le pertenece (ej. <code>CP59_1 · Codificación</code>). El sistema propone coincidencias automáticas por similitud.
          </p>
        </div>
        <div>
          <strong>🎯 ¿Por qué definir el "Máximo de códigos"?</strong>
          <p>
            Define cuántas categorías distintas puede recibir cada respuesta:
            <br />• <strong>1 código (Monocódigo):</strong> Para preguntas de razón única o principal (ej. <i>"¿Cuál es el motivo principal de compra?"</i>). Se asignará solo el código más representativo.
            <br />• <strong>2 o más códigos (Multicódigo):</strong> Para preguntas abiertas donde el encuestado menciona varias ideas en una sola respuesta (ej. mencionó a la vez <i>"precio bajo"</i> y <i>"buen servicio"</i>).
          </p>
        </div>
      </div>
      {(!preview && !usingSaved) ? <p className="muted">Sube el libro o reutiliza catálogos guardados para relacionarlos con las columnas seleccionadas.</p> : questions.map((question) => <div className="mapping-row" key={question.column_name}>
        <div className="mapping-header">
          <strong className="mono">Pregunta: {question.column_name}</strong>
          <span className="chip">
            {question.max_labels === 1 ? "1 código (Monocódigo)" : `Hasta ${question.max_labels} códigos (Multicódigo)`}
          </span>
        </div>
        <div className="mapping-fields">
          <label>Catálogo<select aria-label={`Catálogo ${question.column_name}`} value={question.catalog_key} onChange={(event) => chooseCatalog(question.column_name, event.target.value)}>
            <option value="">Elegir catálogo</option>
            {usingSaved
              ? books.map((book) => (
                  <option key={book.id} value={book.id}>
                    {book.name}
                  </option>
                ))
              : preview?.catalogs.map((catalog) => (
                  <option key={catalog.key} value={catalog.key} disabled={!catalog.compatible}>
                    {catalog.field_id} · {catalog.sheet}{!catalog.compatible ? " · No compatible" : ""}
                  </option>
                ))}
          </select></label>
          <label>Máximo de códigos<select aria-label={`Máximo de códigos ${question.column_name}`} value={question.max_labels} onChange={(event) => { setConfirmed(false); setQuestions((previous) => previous.map((item) => item.column_name === question.column_name ? { ...item, max_labels: Number(event.target.value) } : item)); }}>
            {[1, 2, 3, 4, 5, 6].map((maximum) => <option key={maximum} value={maximum}>{maximum === 1 ? "1 (Monocódigo · 1 código por respuesta)" : `${maximum} (Multicódigo · hasta ${maximum} códigos)`}</option>)}
          </select></label>
        </div>
      </div>)}
      <div className="row between wrap"><button type="button" className="button primary" disabled={!canConfirm || !!busy || confirmed} onClick={() => void confirm()}>{busy === "confirm" ? "Confirmando correspondencias…" : "Confirmar correspondencias"}</button>{confirmed && <p role="status" className="upload-success"><Check size={16} />Correspondencias confirmadas.</p>}</div>
      {error && <p className="field-error" role="alert">{error}</p>}
    </section>
    <section className="panel form-stack" aria-label="Preparar ejecución">
      <div>
        <span className="eyebrow">05 · REVISIÓN DE ENUNCIADOS Y PLAN</span>
        <h2>Preparar ejecución</h2>
        <p className="muted">Comprueba el texto completo de cada pregunta. Puedes corregirlo sin cambiar su catálogo.</p>
      </div>
      <div className="helper-box">
        <strong>💡 ¿Por qué revisar el texto de la pregunta?</strong>
        <p>El sistema lee este enunciado para comprender exactamente el contexto semántico de cada respuesta (ej. si la pregunta indaga por razones de agrado, sugerencias de cambio o quejas) y clasificar con precisión.</p>
      </div>
      {!confirmed ? <p className="muted">Confirma las correspondencias antes de preparar.</p> : questions.map((question) => <label key={question.column_name}>Texto de la pregunta · {question.column_name}<textarea aria-label={`Pregunta ${question.column_name}`} rows={3} maxLength={2000} value={question.question_text} onChange={(event) => setQuestions((previous) => previous.map((item) => item.column_name === question.column_name ? { ...item, question_text: event.target.value } : item))} /><small>{question.question_text.length} / 2000 caracteres</small></label>)}
      <div className="row between wrap"><label className="job-name">Nombre de la ejecución<input value={jobName} onChange={(event) => setJobName(event.target.value)} /></label><button type="button" className="button primary" disabled={!ready || !!busy} onClick={() => void prepare()}>{busy === "job" ? "Preparando ejecución…" : "Preparar ejecución"}<ArrowRight size={16} /></button></div>
      <small className="muted">Preparar guarda el plan. Comienza la codificación por separado desde el monitor cuando esté listo.</small>
      <span className="sr-only">{books.length} catálogos guardados disponibles</span>
    </section>
  </div>;
}

