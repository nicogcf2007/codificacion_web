import { useEffect, useState } from "react";
import { Play, Pause, ArrowRight, Radio, AlertCircle } from "lucide-react";
import { api, message, SessionExpired } from "./api";
import { Status, Metric, Modal, number } from "./ui";
import type { Job, CodedRecord } from "./types";

export function getPauseTitle(reason: string | null): string {
  if (!reason) return "La codificación está en pausa";
  const lower = reason.toLowerCase();
  if (lower.includes("saldo") || lower.includes("cuota")) {
    return "Pausa por saldo insuficiente o cuota de IA";
  }
  if (lower.includes("credencial") || lower.includes("api key") || lower.includes("clave")) {
    return "Pausa por credencial de acceso no configurada";
  }
  if (lower.includes("servidor reiniciado")) {
    return "Pausa por reinicio del servidor";
  }
  if (lower.includes("pausa solicitada")) {
    return "Pausa solicitada por el usuario";
  }
  if (lower.includes("incierto")) {
    return "Pausa por resultado incierto de red";
  }
  return "La codificación está en pausa";
}

export function getActionGuide(reason: string | null): { cause: string; action: string } | null {
  if (!reason) return null;
  const lower = reason.toLowerCase();
  if (lower.includes("saldo") || lower.includes("cuota")) {
    return {
      cause: "La cuenta de IA no tiene saldo disponible o alcanzó el límite de gasto mensual.",
      action: "Recarga saldo en platform.openai.com/billing o amplía el límite mensual de facturación. Luego haz clic en «Reanudar codificación».",
    };
  }
  if (lower.includes("credencial") || lower.includes("api key") || lower.includes("clave")) {
    return {
      cause: "La clave de acceso (API Key) no está configurada o fue invalidada en el servidor.",
      action: "Verifica que la variable OPENAI_API_KEY esté correctamente configurada en el servidor y haz clic en «Reanudar codificación».",
    };
  }
  if (lower.includes("servidor reiniciado")) {
    return {
      cause: "El servidor se reinició o actualizó mientras el proceso estaba activo. Todos los datos previos quedaron guardados.",
      action: "Haz clic directamente en «Reanudar codificación» para continuar desde el punto de control sin repetir datos.",
    };
  }
  if (lower.includes("pausa solicitada")) {
    return {
      cause: "La codificación fue detenida temporalmente por un usuario.",
      action: "Cuando estés listo para continuar, haz clic en «Reanudar codificación».",
    };
  }
  if (lower.includes("incierto") || lower.includes("red")) {
    return {
      cause: "Ocurrió una interrupción de conexión o respuesta incompleta de la red.",
      action: "Marca la casilla de confirmación abajo y haz clic en «Reanudar codificación» para reintentar el registro pendiente.",
    };
  }
  return {
    cause: "Se presentó una interrupción durante el procesamiento.",
    action: "Revisa el motivo indicado arriba. Si el problema persiste tras reanudar, contacta al administrador.",
  };
}

export function Monitor({
  job,
  executionUnavailable = false,
  onUpdated,
  onReview,
  onAnalytics,
  report,
}: {
  job: Job;
  executionUnavailable?: boolean;
  onUpdated: (job: Job) => void;
  onReview: () => void;
  onAnalytics: () => void;
  report: (message: string) => void;
}) {
  const [live, setLive] = useState(job);
  const [records, setRecords] = useState<CodedRecord[]>([]);
  const [connection, setConnection] = useState("Actualizando progreso…");
  const [busy, setBusy] = useState(false);
  const [alertOpen, setAlertOpen] = useState(false);
  const [retryUncertain, setRetryUncertain] = useState(false);
  useEffect(() => {
    setLive(job);
  }, [job]);
  useEffect(() => {
    const controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout>;
    const connect = async () => {
      try {
        await api.observe(
          job.id,
          (snapshot) => {
            if (controller.signal.aborted) return;
            setLive(snapshot.job);
            setRecords(snapshot.records);
            onUpdated(snapshot.job);
            setConnection(
              snapshot.job.status === "RUNNING"
                ? "Actualizando en vivo"
                : "Resultados guardados",
            );
          },
          controller.signal,
        );
      } catch (problem) {
        if (controller.signal.aborted || problem instanceof SessionExpired) return;
        setConnection("Actualizando progreso…");
        try {
          const current = await api.request<Job>(`/jobs/${job.id}`, {
            signal: controller.signal,
          });
          setLive(current);
          onUpdated(current);
        } catch (fallback) {
          if (!controller.signal.aborted) report(message(fallback));
        }
      }
      if (!controller.signal.aborted)
        timeout = setTimeout(() => void connect(), 2000);
    };
    void connect();
    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [job.id, onUpdated, report]);
  useEffect(() => {
    if (live.status === "PAUSED" && live.pause_reason) {
      setAlertOpen(true);
      setRetryUncertain(false);
    }
  }, [live.status, live.pause_reason]);
  const uncertain =
    live.pause_reason?.toLocaleLowerCase().includes("incierto") || false;
  const guide = getActionGuide(live.pause_reason);
  const pauseTitle = getPauseTitle(live.pause_reason);
  const unavailable = executionUnavailable || live.provider_mode === "blocked";
  const act = async (action: "start" | "pause" | "resume") => {
    if (busy || (unavailable && action !== "pause")) return;
    setBusy(true);
    try {
      const current = await api.post<Job>(
        `/jobs/${job.id}/${action}`,
        action === "resume" ? { retry_uncertain: retryUncertain } : {},
      );
      setLive(current);
      onUpdated(current);
      setAlertOpen(false);
    } catch (error) {
      report(message(error));
    } finally {
      setBusy(false);
    }
  };
  const metrics = live.metrics;
  return (
    <div className="monitor-layout">
      <section className="panel execution">
        <div className="row between wrap">
          <div>
            <span className="eyebrow">EJECUCIÓN PERSISTENTE</span>
            <h2>{live.name}</h2>
            <div className="row">
              <Status status={live.status} />
              <span className="muted small-text">
                <Radio size={12} />
                {connection}
              </span>
            </div>
          </div>
          <div className="row wrap">
            {live.status === "RUNNING" ? (
              <button
                className="button"
                disabled={busy}
                onClick={() => void act("pause")}
              >
                <Pause size={15} />
                Pausar
              </button>
            ) : (
              (live.status === "PENDING" || live.status === "PAUSED") && (
                <button
                  className="button primary"
                  disabled={busy || unavailable}
                  onClick={() =>
                    live.status === "PAUSED" && uncertain
                      ? setAlertOpen(true)
                      : void act(live.status === "PAUSED" ? "resume" : "start")
                  }
                >
                  <Play size={15} />
                  {live.status === "PAUSED"
                    ? "Reanudar codificación"
                    : "Iniciar codificación"}
                </button>
              )
            )}
            <button className="button" onClick={onReview}>
              Revisión humana
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
        <div className="progress-label row between">
          <span>
            {number(live.processed_records)} / {number(live.total_records)}{" "}
            respuestas
          </span>
          <strong className="mono">{number(live.progress)}%</strong>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label="Progreso de codificación"
          aria-valuenow={live.progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div style={{ width: `${live.progress}%` }} />
        </div>
        {unavailable && (
          <div className="notice">
            <AlertCircle size={16} />
            Ejecución no disponible. Contacta al administrador
          </div>
        )}
        {live.provider_mode === "demo" && (
          <div className="notice">
            Datos de demostración; no usar como resultados reales
          </div>
        )}
        {live.pause_reason && (
          <div
            className="notice warning"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.35rem",
              alignItems: "flex-start",
            }}
          >
            <div className="row" style={{ gap: "0.5rem", alignItems: "center" }}>
              <AlertCircle size={16} />
              <strong>{pauseTitle}</strong>
            </div>
            <p style={{ margin: 0 }}>{live.pause_reason}</p>
            {guide && (
              <p
                style={{
                  margin: "0.2rem 0 0",
                  color: "var(--foreground)",
                  fontSize: "0.85rem",
                }}
              >
                👉 <strong>Qué hacer:</strong> {guide.action}
              </p>
            )}
          </div>
        )}
        <div className="metric-grid">
          <Metric
            label="Velocidad"
            value={`${number(metrics.records_per_second)} reg/s`}
            note={
              metrics.eta_seconds === null
                ? "Tiempo restante no disponible"
                : `Tiempo restante: ${Math.ceil(metrics.eta_seconds)} segundos`
            }
          />
          <Metric label="Respuestas pendientes" value={number(Math.max(0, live.total_records - live.processed_records))} note="Por codificar en este trabajo" />
          <Metric label="Preguntas" value={number(live.questions.length)} note="Definidas en el plan" />
          <Metric label="Avance" value={`${number(live.progress)}%`} note="Sobre el total de respuestas" />
        </div>
      </section>
      <div className="monitor-grid">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Actividad de codificación</h2>
              <p>Últimas respuestas guardadas del trabajo.</p>
            </div>
            <span
              className={`status ${live.status === "RUNNING" ? "status-running" : ""}`}
            >
              <span />
              {live.status === "RUNNING" ? "En vivo" : "Guardado"}
            </span>
          </div>
          <div className="activity-list">
            {records.length ? (
              [...records].reverse().map((record) => (
                <div className="activity-row" key={record.id}>
                  <span className="activity-dot" />
                  <div>
                    <p>{record.text_original || "(vacío)"}</p>
                    <small>
                      {record.column_name} · fila {record.response_id + 2} ·{" "}
                      {record.was_grouped ? "Agrupada" : "Directa"}
                    </small>
                  </div>
                  <code className="code-pill">{record.codes.join(";")}</code>
                </div>
              ))
            ) : (
              <div className="empty muted">
                La actividad aparecerá cuando se guarden resultados.
              </div>
            )}
          </div>
        </section>
        <aside className="panel form-stack">
          <span className="eyebrow">REVISIÓN Y ENTREGA</span>
          <h2>Continúa con los resultados</h2>
          <p className="muted">Revisa las asignaciones que requieren una decisión humana y consulta la distribución por pregunta antes de exportar.</p>
          <p className="muted">Los resultados confirmados se conservan al pausar y reanudar. Un resultado incierto requiere confirmación explícita.</p>
          <button className="button" onClick={onAnalytics}>
            Ver distribución y exportar
            <ArrowRight size={15} />
          </button>
        </aside>
      </div>
      <Modal
        open={alertOpen}
        onOpenChange={setAlertOpen}
        title={pauseTitle}
        description={
          uncertain
            ? "Un resultado no pudo confirmarse por una interrupción. Los resultados anteriores permanecen guardados con seguridad."
            : "Los resultados confirmados hasta el momento permanecen guardados con seguridad."
        }
      >
        <div className="form-stack">
          {live.pause_reason && (
            <div
              className="notice warning"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.25rem",
                alignItems: "flex-start",
              }}
            >
              <strong>Motivo del estado en pausa:</strong>
              <p style={{ margin: 0 }}>{live.pause_reason}</p>
            </div>
          )}

          {guide && (
            <div
              className="panel form-stack"
              style={{
                background: "var(--surface-sunken)",
                padding: "0.85rem 1rem",
                border: "1px solid var(--border)",
              }}
            >
              <span className="eyebrow" style={{ color: "var(--primary)" }}>
                SOLUCIÓN RECOMENDADA
              </span>
              <p style={{ margin: 0, fontSize: "0.9rem" }}>
                <strong>Causa:</strong> {guide.cause}
              </p>
              <p style={{ margin: 0, fontSize: "0.9rem" }}>
                <strong>¿Qué debes hacer?</strong> {guide.action}
              </p>
            </div>
          )}

          {uncertain && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={retryUncertain}
                onChange={(event) => setRetryUncertain(event.target.checked)}
              />
              Entiendo que reintentar un resultado incierto podría generar un
              cargo adicional.
            </label>
          )}
          <button
            className="button primary"
            disabled={busy || unavailable || (uncertain && !retryUncertain)}
            onClick={() => void act("resume")}
          >
            <Play size={15} />
            Reanudar codificación
          </button>
        </div>
      </Modal>
    </div>
  );
}
