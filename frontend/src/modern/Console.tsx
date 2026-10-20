import { useCallback, useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  Layers3,
  FolderKanban,
  Activity,
  Inbox,
  BarChart3,
  Users,
  ClipboardList,
  LayoutDashboard,
  ArrowLeft,
  Plus,
  RefreshCw,
  ArrowUpRight,
  X,
} from "lucide-react";
import { api, message } from "./api";
import { Workspace } from "./Workspace";
import { Composer } from "./Composer";
import { Monitor } from "./Monitor";
import { ReviewInbox } from "./Review";
import { AnalyticsPanel } from "./Analytics";
import { AdminPanel } from "./Admin";
import { Empty, Status } from "./ui";
import { SessionBoundary, SessionProfile, ThemeToggle } from "./Session";
import type { Project, Job, Health, CodedRecord, Analytics, User } from "./types";

type View =
  | "projects"
  | "configure"
  | "executions"
  | "monitor"
  | "review"
  | "analytics"
  | "users"
  | "audit"
  | "overview";
const titles: Record<View, string> = {
  projects: "Espacio de proyectos",
  configure: "Preparar codificación",
  executions: "Ejecuciones",
  monitor: "Monitor de ejecución",
  review: "Revisión humana",
  analytics: "Resultados y exportación",
  users: "Usuarios",
  audit: "Auditoría global",
  overview: "Resumen administrativo",
};

export default function Console() {
  return <SessionBoundary>{(user, onLogout, onUser) => <ConsoleWorkspace key={user.id} user={user} onLogout={onLogout} onUser={onUser} />}</SessionBoundary>;
}

function ConsoleWorkspace({ user, onLogout, onUser }: { user: User; onLogout: () => Promise<void>; onUser: (user: User) => void }) {
  const [view, setView] = useState<View>("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [records, setRecords] = useState<CodedRecord[]>([]);
  const [pending, setPending] = useState(0);
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const reducedMotion = useReducedMotion();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [view]);
  const report = useCallback((text: string) => setError(text), []);
  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    setRevision((value) => value + 1);
    try {
      const status = await api.request<Health>("/health");
      setHealth(status);
      const [loadedProjects, loadedJobs] = await Promise.all([
        api.request<{ projects: Project[] }>("/projects"),
        api.request<{ jobs: Job[] }>("/jobs"),
      ]);
      setProjects(loadedProjects.projects);
      setJobs(loadedJobs.jobs);
    } catch (problem) {
      report(message(problem));
    } finally {
      setLoading(false);
    }
  }, [report]);
  useEffect(() => {
    void reload();
  }, [reload]);
  const updateJob = useCallback((current: Job) => {
    setJob(current);
    if (current.status !== "PENDING") {
      setNotice((existing) =>
        existing === "Plan preparado. Puedes iniciar la codificación desde el monitor."
          ? ""
          : existing,
      );
    }
    setJobs((previous) =>
      previous.map((item) => (item.id === current.id ? current : item)),
    );
  }, []);
  const jobId = job?.id;
  const refreshReview = useCallback(async () => {
    if (!jobId) return;
    try {
      const [queue, counts, current] = await Promise.all([
        api.request<{ records: CodedRecord[] }>(
          `/jobs/${jobId}/records?review_only=true`,
        ),
        api.request<Analytics>(`/jobs/${jobId}/analytics`),
        api.request<Job>(`/jobs/${jobId}`),
      ]);
      setRecords(queue.records);
      setPending(counts.pending_review);
      updateJob(current);
    } catch (problem) {
      report(message(problem));
    }
  }, [jobId, report, updateJob]);
  useEffect(() => {
    if (view === "review") void refreshReview();
  }, [view, refreshReview]);
  const selectProject = (selected: Project) => {
    setProject(selected);
    setView("configure");
    setError("");
  };
  const selectJob = (selected: Job) => {
    setJob(selected);
    setProject(
      projects.find((item) => item.id === selected.project_id) || null,
    );
    setView("monitor");
    setError("");
  };
  const created = (current: Job) => {
    setJobs((previous) => [current, ...previous]);
    setJob(current);
    setView("monitor");
    setNotice("Plan preparado. Puedes iniciar la codificación desde el monitor.");
    void reload();
  };
  const nav = [
    { id: "projects" as View, label: "Proyectos", icon: FolderKanban },
    { id: "executions" as View, label: "Ejecuciones", icon: Activity },
    { id: "review" as View, label: "Revisión humana", icon: Inbox },
    { id: "analytics" as View, label: "Resultados", icon: BarChart3 },
    ...(user.role === "ADMIN" ? [
      { id: "overview" as View, label: "Resumen administrativo", icon: LayoutDashboard },
      { id: "users" as View, label: "Usuarios", icon: Users },
      { id: "audit" as View, label: "Auditoría global", icon: ClipboardList },
    ] : []),
  ];
  const visibleJobs = project
    ? jobs.filter((item) => item.project_id === project.id)
    : jobs;
  return (
    <div className="cnc-app">
      <a className="skip-link" href="#workspace">
        Ir al contenido
      </a>
      <aside className="app-sidebar">
        <div className="brand">
          <span className="brand-symbol">
            <Layers3 size={21} />
          </span>
          <div>
            <strong>
              CNC<span> / </span>Studio
            </strong>
            <small>CODIFICACIÓN CUALITATIVA</small>
          </div>
        </div>
        <div className="workspace-switch">
          <span className="avatar">CN</span>
          <div>
            <strong>Centro Nacional de Consultoría</strong>
            <small>Espacio de análisis</small>
          </div>
        </div>
        <span className="nav-section">ESPACIO DE TRABAJO</span>
        <nav aria-label="Secciones del espacio">
          {nav.map((item) => (
            <button
              key={item.id}
              className={
                view === item.id ||
                (item.id === "executions" && view === "monitor") ||
                (item.id === "projects" && view === "configure")
                  ? "active"
                  : ""
              }
              onClick={() => {
                setView(item.id);
                setError("");
              }}
            >
              <item.icon size={17} />
              {item.label}
              {item.id === "executions" &&
                jobs.some((item) => item.status === "RUNNING") && (
                  <span className="nav-dot" />
                )}
            </button>
          ))}
        </nav>
        {project && (
          <div className="active-study">
            <span className="nav-section">ESTUDIO ACTIVO</span>
            <strong>{project.name}</strong>
            <small>{project.client || "Sin cliente"}</small>
            <button
              className="button small"
              onClick={() => setView("configure")}
            >
              <Plus size={14} />
              Nueva ejecución
            </button>
            <button
              className="text-button"
              onClick={() => {
                setProject(null);
                setView("projects");
              }}
            >
              Cambiar estudio
            </button>
          </div>
        )}
        <div className="sidebar-bottom">
          <ThemeToggle />
          <small className="sidebar-caption">
            CNC · Herramientas de investigación
          </small>
        </div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Studio</span>
            <span>/</span>
            <strong>{project?.name || "Todos los estudios"}</strong>
          </div>
          <div className="row">
            <button
              className="icon-button"
              aria-label="Actualizar espacio"
              onClick={() => void reload()}
            >
              <RefreshCw size={17} />
            </button>
            <SessionProfile user={user} onLogout={onLogout} onUser={onUser} />
          </div>
        </header>
        <main id="workspace" className="content">
          <div className="page-heading">
            <div>
              <span className="eyebrow">CNC / RESEARCH OPERATIONS</span>
              <h1>{titles[view]}</h1>
              <p>
                {view === "projects"
                  ? "Convierte respuestas abiertas en decisiones trazables."
                  : view === "configure"
                    ? project?.name
                    : job &&
                        (view === "review" ||
                          view === "analytics" ||
                          view === "monitor")
                      ? job.name
                      : "Gestiona trabajos guardados y retoma donde quedaste."}
              </p>
            </div>
            {view !== "projects" && (
              <button
                className="button small"
                onClick={() => setView("projects")}
              >
                <ArrowLeft size={15} />
                Proyectos
              </button>
            )}
          </div>
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <div className="row">
                <button aria-label="Cerrar error" onClick={() => setError("")}>
                  <X size={16} />
                </button>
              </div>
            </div>
          )}
          {health?.provider_mode === "demo" && <div className="notice" role="status">Datos de demostración; no usar como resultados reales</div>}
          {notice && (
            <div className="notice row between" role="status">
              <span>{notice}</span>
              <button
                className="icon-button"
                aria-label="Cerrar aviso"
                onClick={() => setNotice("")}
              >
                <X size={15} />
              </button>
            </div>
          )}
          <motion.div
            key={`${view}-${view === "configure" ? project?.id : ""}`}
            initial={reducedMotion ? false : { opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.16 }}
          >
            {view === "projects" && (
              <Workspace
                projects={projects}
                loading={loading}
                onSelect={selectProject}
                onCreate={async (name, client) => {
                  try {
                    const current = await api.post<Project>("/projects", {
                      name,
                      client,
                    });
                    setProjects((previous) => [current, ...previous]);
                    setNotice(
                      "Proyecto guardado. Carga una base y define su catálogo.",
                    );
                    selectProject(current);
                  } catch (problem) {
                    report(message(problem));
                  }
                }}
              />
            )}
            {view === "configure" &&
              (project ? (
                <Composer
                  key={project.id}
                  project={project}
                  onCreated={created}
                  report={report}
                />
              ) : (
                <Empty
                  title="Selecciona un estudio"
                  description="Los datos y catálogos siempre pertenecen a un proyecto."
                />
              ))}
            {view === "executions" && (
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>
                      {project
                        ? `Trabajos de ${project.name}`
                        : "Todas las ejecuciones"}
                    </h2>
                    <p>
                      Progreso y resultados sobreviven a la sesión del
                      navegador.
                    </p>
                  </div>
                  <span className="muted">{visibleJobs.length} trabajos</span>
                </div>
                {visibleJobs.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Ejecución</th>
                          <th>Estado</th>
                          <th>Progreso</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {visibleJobs.map((current) => (
                          <tr key={current.id}>
                            <td>
                              <strong>{current.name}</strong>
                              <small>
                                {new Date(current.created_at).toLocaleString(
                                  "es-CO",
                                )}
                              </small>
                            </td>
                            <td>
                              <Status status={current.status} />
                            </td>
                            <td>
                              <div className="mini-progress">
                                <i style={{ width: `${current.progress}%` }} />
                              </div>
                              <small>
                                {current.processed_records} /{" "}
                                {current.total_records}
                              </small>
                            </td>
                            <td>
                              <button
                                className="button small"
                                onClick={() => selectJob(current)}
                              >
                                Abrir
                                <ArrowUpRight size={14} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title="Todavía no hay ejecuciones"
                    description="Prepara un estudio para guardar su primer trabajo."
                  />
                )}
              </section>
            )}
            {view === "monitor" && job && (
              <Monitor
                key={job.id}
                job={job}
                executionUnavailable={!health || health.provider_mode === "blocked"}
                onUpdated={updateJob}
                report={report}
                onReview={() => setView("review")}
                onAnalytics={() => setView("analytics")}
              />
            )}
            {view === "review" &&
              (job ? (
                <ReviewInbox
                  key={job.id}
                  job={job}
                  records={records}
                  totalPending={pending}
                  onRefresh={refreshReview}
                  report={report}
                />
              ) : (
                <Empty
                  title="Elige una ejecución para revisar"
                  description="Abre un trabajo en Ejecuciones y entra a su bandeja de revisión."
                >
                  <button
                    className="button primary"
                    onClick={() => setView("executions")}
                  >
                    Ver ejecuciones
                  </button>
                </Empty>
              ))}
            {view === "analytics" &&
              (job ? (
                <AnalyticsPanel key={job.id} job={job} report={report} />
              ) : (
                <Empty
                  title="Resultados vinculados a cada trabajo"
                  description="Selecciona una ejecución para consultar sus frecuencias y exportar el archivo original codificado."
                >
                  <button
                    className="button primary"
                    onClick={() => setView("executions")}
                  >
                    Ver ejecuciones
                  </button>
                </Empty>
              ))}
            {user.role === "ADMIN" && (view === "users" || view === "audit" || view === "overview") && <AdminPanel key={`${view}-${revision}`} user={user} view={view} report={report} />}
          </motion.div>
          <footer className="workspace-footer">
            <span>CNC · Espacio compartido de investigación</span>
            <span>Proyectos y decisiones de tu equipo</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
