import { useState, useEffect, useCallback, useMemo } from "react";
import { Check, ChevronDown, ChevronUp, Tags, RefreshCw } from "lucide-react";
import { api, message } from "./api";
import { Empty, Modal } from "./ui";
import type { Job, CodedRecord } from "./types";

function reviewReason(reason: string | null): string {
  if (!reason) return "Requiere revisión humana.";
  if (/salida inv[aá]lida/i.test(reason)) return "Asignación inválida: requiere revisión humana.";
  if (/modelo|motor|proveedor|openai|api|gpt-/i.test(reason)) return "Asignación que requiere revisión humana.";
  return reason;
}

export function ReviewInbox({
  job,
  records,
  totalPending,
  onRefresh,
  report,
}: {
  job: Job;
  records: CodedRecord[];
  totalPending: number;
  onRefresh: () => Promise<void>;
  report: (error: string) => void;
}) {
  const [index, setIndex] = useState(0);
  const [codes, setCodes] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [batchOpen, setBatchOpen] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const active = records[Math.min(index, Math.max(0, records.length - 1))];
  const question = job.questions.find((q) => q.id === active?.question_id);
  const categories = useMemo(() => {
    const result = [...(question?.categories || [])];
    for (const category of [
      { code: "77", label: "Otro" },
      { code: "88", label: "Ninguno / satisfacción" },
      { code: "99", label: "No sabe / no responde" },
    ]) {
      if (!result.some((c) => c.code === category.code)) result.push(category);
    }
    return result;
  }, [question]);
  useEffect(() => {
    setCodes(active?.codes || []);
  }, [active]);
  const approve = useCallback(async () => {
    if (!active || busy || !codes.length || job.status === "RUNNING") return;
    setBusy(true);
    try {
      await api.request(`/jobs/${job.id}/records/${active.id}`, {
        method: "PATCH",
        body: JSON.stringify({ codes, review_status: "APPROVED" }),
      });
      await onRefresh();
      setSelected([]);
    } catch (error) {
      report(message(error));
    } finally {
      setBusy(false);
    }
  }, [active, busy, codes, job.id, job.status, onRefresh, report]);
  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if (!active || batchOpen || event.repeat || event.ctrlKey || event.altKey || event.metaKey) return;
      if (
        event.target instanceof HTMLElement &&
        (event.target.matches("input,textarea,select") ||
          event.target.isContentEditable)
      )
        return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setIndex((value) => Math.min(value + 1, records.length - 1));
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setIndex((value) => Math.max(value - 1, 0));
      }
      if (/^[1-9]$/.test(event.key)) {
        const category = categories[Number(event.key) - 1];
        if (category) {
          event.preventDefault();
          setCodes([category.code]);
        }
      }
      if (event.key === "Enter") {
        event.preventDefault();
        void approve();
      }
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [active, approve, batchOpen, categories, records.length]);
  if (!active)
    return (
      <>
      {job.provider_mode === "demo" && <div className="notice" role="status">Datos de demostración; no usar como resultados reales</div>}
      <Empty
        title="Bandeja de revisión al día"
        description="Los casos con código 77, salida inválida o agrupamiento difuso aparecerán aquí. No se inventan puntuaciones de confianza."
      >
        <button className="button" onClick={() => void onRefresh()}>
          <RefreshCw size={15} />
          Actualizar
        </button>
      </Empty>
      </>
    );

  const toggleCode = (code: string) =>
    setCodes((previous) => {
      if (previous.includes(code)) return previous.filter((c) => c !== code);
      if (code === "88" || code === "99") return [code];
      const valid = previous.filter((c) => c !== "88" && c !== "99");
      return valid.length < (question?.max_labels || 1)
        ? [...valid, code]
        : [code];
    });
  return (
    <>
      {job.provider_mode === "demo" && <div className="notice" role="status">Datos de demostración; no usar como resultados reales</div>}
      <div className="review-toolbar row between wrap">
        <span>
          <strong>{totalPending}</strong> por revisar{" "}
          <span className="muted">· mostrando hasta 200</span>
        </span>
        <div className="row">
          <button
            className="button small"
            disabled={!selected.length || busy || job.status === "RUNNING"}
            onClick={() => setBatchOpen(true)}
          >
            <Tags size={15} />
            Nueva categoría en lote ({selected.length})
          </button>
          <button
            className="icon-button"
            aria-label="Actualizar revisión"
            onClick={() => void onRefresh()}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>
      {job.status === "RUNNING" && (
        <div className="notice">
          Pausa la ejecución para guardar decisiones humanas.
        </div>
      )}
      <div className="review-layout">
        <div className="panel review-list">
          {records.map((record, i) => (
            <div
              className={`review-row ${active.id === record.id ? "active" : ""}`}
              key={record.id}
            >
              <input
                aria-label={`Seleccionar registro ${record.response_id + 1}`}
                type="checkbox"
                checked={selected.includes(record.id)}
                onChange={(event) =>
                  setSelected((previous) =>
                    event.target.checked
                      ? [...previous, record.id]
                      : previous.filter((id) => id !== record.id),
                  )
                }
              />
              <button onClick={() => setIndex(i)}>
                <span className="row between">
                  <code>
                    {record.column_name} · fila {record.response_id + 2}
                  </code>
                  <span className="code-pill">{record.codes.join(";")}</span>
                </span>
                <span className="response-preview">{record.text_original}</span>
                <small>{reviewReason(record.review_reason)}</small>
              </button>
            </div>
          ))}
        </div>
        <section className="panel review-detail form-stack">
          <div className="row between">
            <span className="eyebrow">DECISIÓN DEL ANALISTA</span>
            <div className="row">
              <button
                className="icon-button"
                aria-label="Registro anterior"
                disabled={index === 0}
                onClick={() => setIndex((i) => Math.max(0, i - 1))}
              >
                <ChevronUp size={18} />
              </button>
              <button
                className="icon-button"
                aria-label="Registro siguiente"
                disabled={index >= records.length - 1}
                onClick={() =>
                  setIndex((i) => Math.min(records.length - 1, i + 1))
                }
              >
                <ChevronDown size={18} />
              </button>
            </div>
          </div>
          <h2>{question?.question_text || active.column_name}</h2>
          <blockquote>{active.text_original}</blockquote>
          <div className="review-reason">
            {reviewReason(active.review_reason)}
            <small>
              {active.confidence === null
                ? "Confianza no disponible"
                : `Confianza: ${active.confidence}`}
            </small>
          </div>
          <div>
            <span className="muted">
              Códigos asignados · máximo {question?.max_labels || 1}
            </span>
            <div className="review-categories">
              {categories.map((category, i) => (
                <button
                  className={`category-choice ${codes.includes(category.code) ? "selected" : ""}`}
                  aria-pressed={codes.includes(category.code)}
                  key={category.code}
                  onClick={() => toggleCode(category.code)}
                >
                  <code>{category.code}</code>
                  <span>{category.label}</span>
                  {i < 9 && <kbd>{i + 1}</kbd>}
                </button>
              ))}
            </div>
          </div>
          <button
            className="button primary"
            disabled={busy || !codes.length || job.status === "RUNNING"}
            onClick={() => void approve()}
          >
            <Check size={16} />
            {busy ? "Guardando…" : "Aprobar y continuar"}
          </button>
          <small className="keyboard-help">
            <kbd>↑</kbd>
            <kbd>↓</kbd> navegar · <kbd>1–9</kbd> elegir · <kbd>Enter</kbd>{" "}
            aprobar. Se ignoran atajos al escribir.
          </small>
        </section>
      </div>
      <Modal
        open={batchOpen}
        onOpenChange={setBatchOpen}
        title="Crear categoría humana"
        description="Aplica un código nuevo a los registros seleccionados de una sola pregunta. La decisión queda en la auditoría."
      >
        <form
          className="form-stack"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            try {
              await api.post(`/jobs/${job.id}/review/batch`, {
                record_ids: selected,
                code: newCode,
                label: newLabel,
              });
              await onRefresh();
              setSelected([]);
              setBatchOpen(false);
              setNewCode("");
              setNewLabel("");
            } catch (error) {
              report(message(error));
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Nuevo código
            <input
              aria-label="Nuevo código"
              maxLength={2}
              pattern="[0-9]{2}"
              required
              value={newCode}
              onChange={(event) => setNewCode(event.target.value)}
            />
          </label>
          <label>
            Etiqueta de la categoría
            <input
              required
              value={newLabel}
              onChange={(event) => setNewLabel(event.target.value)}
            />
          </label>
          <button
            className="button primary"
            disabled={busy || !/^\d{2}$/.test(newCode) || !newLabel.trim()}
          >
            Aplicar a {selected.length} registros
          </button>
        </form>
      </Modal>
    </>
  );
}
