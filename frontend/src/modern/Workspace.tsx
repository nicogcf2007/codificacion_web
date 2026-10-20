import { useState } from "react";
import { ArrowUpRight, Search, Plus } from "lucide-react";
import type { Project } from "./types";
import { Empty } from "./ui";

export function Workspace({
  projects,
  loading,
  onCreate,
  onSelect,
}: {
  projects: Project[];
  loading: boolean;
  onCreate: (name: string, client: string) => Promise<void>;
  onSelect: (project: Project) => void;
}) {
  const [query, setQuery] = useState("");
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [saving, setSaving] = useState(false);
  const visible = projects.filter((project) =>
    `${project.name} ${project.client}`
      .toLocaleLowerCase()
      .includes(query.toLocaleLowerCase()),
  );
  return (
    <div className="workspace-grid">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Estudios en tu espacio</h2>
            <p>Datos, catálogos y ejecuciones en un solo lugar.</p>
          </div>
          <span className="muted mono">{projects.length} proyectos</span>
        </div>
        <div className="search">
          <Search size={17} />
          <input
            aria-label="Buscar proyectos"
            placeholder="Buscar estudio o cliente…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        {loading ? (
          <div className="empty" role="status">
            Cargando proyectos…
          </div>
        ) : visible.length ? (
          <div className="project-list">
            {visible.map((project) => (
              <button
                key={project.id}
                className="project-row"
                onClick={() => onSelect(project)}
              >
                <span className="project-mark">
                  {project.name.slice(0, 2).toUpperCase()}
                </span>
                <span className="project-name">
                  <strong>{project.name}</strong>
                  <small>
                    {project.client || "Sin cliente"} ·{" "}
                    {new Date(project.created_at).toLocaleDateString("es-CO")}
                  </small>
                </span>
                <span className="project-counts">
                  {project.survey_count} bases
                  <span>{project.job_count} ejecuciones</span>
                </span>
                <ArrowUpRight size={18} />
              </button>
            ))}
          </div>
        ) : (
          <Empty
            title={
              query
                ? "No hay proyectos que coincidan"
                : "Tu próximo estudio comienza aquí"
            }
            description={
              query
                ? "Prueba otro nombre o cliente."
                : "Crea un proyecto y conserva cada ejecución, incluso después de cerrar el navegador."
            }
          />
        )}
      </section>
      <aside>
        <form
          className="panel form-stack"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!name.trim() || saving) return;
            setSaving(true);
            try {
              await onCreate(name.trim(), client.trim());
              setName("");
              setClient("");
            } finally {
              setSaving(false);
            }
          }}
        >
          <div className="row">
            <Plus size={18} />
            <h2>Nuevo proyecto</h2>
          </div>
          <label>
            Nombre del estudio
            <input
              aria-label="Nombre del estudio"
              required
              maxLength={240}
              placeholder="Ej. Experiencia de clientes"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            Cliente
            <input
              aria-label="Cliente"
              maxLength={240}
              placeholder="Organización o área"
              value={client}
              onChange={(event) => setClient(event.target.value)}
            />
          </label>
          <button className="button primary" disabled={!name.trim() || saving}>
            {saving ? "Creando…" : "Crear proyecto"}
          </button>
        </form>
        <div className="sidebar-note">
          <span className="eyebrow">Persistencia primero</span>
          <p>
            El archivo original, los clústeres y los resultados se guardan en la
            base de datos. No necesitas recuperar archivos parciales.
          </p>
        </div>
      </aside>
    </div>
  );
}
