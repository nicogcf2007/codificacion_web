import { useState, useEffect, useCallback } from "react";
import { Download, RefreshCw } from "lucide-react";
import { api, message } from "./api";
import type { Job, Analytics as AnalyticsData } from "./types";
import { Empty, number } from "./ui";

export function AnalyticsPanel({
  job,
  report,
}: {
  job: Job;
  report: (message: string) => void;
}) {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    try {
      setData(await api.request<AnalyticsData>(`/jobs/${job.id}/analytics`));
    } catch (error) {
      report(message(error));
    }
  }, [job.id, report]);
  useEffect(() => {
    void refresh();
  }, [refresh, job.updated_at]);
  const download = async (format: "xlsx" | "csv") => {
    setBusy(true);
    try {
      await api.download(job.id, format);
    } catch (error) {
      report(message(error));
    } finally {
      setBusy(false);
    }
  };
  const max = Math.max(
    1,
    ...(data?.distribution.map((row) => row.count) || []),
  );
  return (
    <section className="panel">
      <div className="panel-head wrap">
        <div>
          <h2>Distribución de códigos</h2>
          <p>
            {job.name} · frecuencias por mención, no porcentajes de personas.
          </p>
        </div>
        <div className="row">
          <button
            className="icon-button"
            aria-label="Actualizar métricas"
            onClick={() => void refresh()}
          >
            <RefreshCw size={17} />
          </button>
          <button
            className="button small"
            disabled={busy || job.status !== "COMPLETED"}
            onClick={() => void download("csv")}
          >
            <Download size={15} />
            CSV
          </button>
          <button
            className="button primary small"
            disabled={busy || job.status !== "COMPLETED"}
            onClick={() => void download("xlsx")}
          >
            <Download size={15} />
            Excel
          </button>
        </div>
      </div>
      {job.provider_mode === "demo" && <div className="notice" role="status">Datos de demostración; no usar como resultados reales</div>}
      {!data ? (
        <div className="empty" role="status">
          Cargando distribución…
        </div>
      ) : (
        <>
          <div className="analytics-summary">
            <span>
              <strong>{number(data.processed_records)}</strong> respuestas
              codificadas
            </span>
            <span>
              <strong>{number(data.pending_review)}</strong> pendientes de
              revisión
            </span>
            <span className="muted">
              Exportación CNC: C[pregunta]_1, C[pregunta]_2…
            </span>
          </div>
          {data.pending_review > 0 && (
            <div className="notice warning">
              La exportación incluirá {data.pending_review} asignaciones aún sin
              validar por un analista.
            </div>
          )}
          {data.distribution.length ? (
            <div className="distribution">
              {data.distribution.map((row, index) => (
                <button
                  className={`bar-row ${selected === index ? "selected" : ""}`}
                  aria-pressed={selected === index}
                  key={index}
                  onClick={() => setSelected(index)}
                >
                  <span className="bar-label">
                    <code>
                      {row.column_name} · {row.code}
                    </code>
                    <span>{row.label}</span>
                  </span>
                  <span className="bar-track">
                    <i style={{ width: `${(row.count / max) * 100}%` }} />
                  </span>
                  <strong className="mono">{number(row.count)}</strong>
                </button>
              ))}
            </div>
          ) : (
            <Empty
              title="Aún no hay asignaciones"
              description="Inicia la codificación para construir la distribución con registros reales del trabajo."
            />
          )}
          {selected !== null && data.distribution[selected] && (
            <div className="chart-detail">
              <code>
                {data.distribution[selected].column_name} ·{" "}
                {data.distribution[selected].code}
              </code>
              <strong>{data.distribution[selected].label}</strong>
              <span>
                {number(data.distribution[selected].count)} menciones en esta
                ejecución
              </span>
            </div>
          )}
          <footer className="panel-footer">
            La exportación usa todos los registros guardados, no solo la página
            visible. Conserva el original y añade códigos de dos dígitos; las
            celdas con posibles fórmulas se neutralizan.
          </footer>
        </>
      )}
    </section>
  );
}
