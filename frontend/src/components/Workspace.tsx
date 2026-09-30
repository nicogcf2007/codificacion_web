import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  createCatalog,
  createProject,
  handleAPIError,
  listCatalogs,
  listJobs,
  listProjects,
  updateCatalog,
} from '../services/api';
import type { Catalog, CatalogEntry, Job, Project } from '../types';

interface WorkspaceProps {
  onBack: () => void;
  onUseProject: (projectId: string, catalogId?: string) => void;
  onOpenJob: (jobId: string) => void;
}

const emptyEntry = (): CatalogEntry => ({ code: '', label: '', description: '', parent_code: null });

const Workspace: React.FC<WorkspaceProps> = ({ onBack, onUseProject, onOpenJob }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [catalogs, setCatalogs] = useState<Catalog[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [selectedCatalogId, setSelectedCatalogId] = useState<string>('');
  const [catalogDraft, setCatalogDraft] = useState<Catalog | null>(null);
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [catalogName, setCatalogName] = useState('');
  const [multiLabel, setMultiLabel] = useState(false);
  const [maxLabels, setMaxLabels] = useState(1);
  const [entries, setEntries] = useState<CatalogEntry[]>([emptyEntry()]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const [loadedProjects, loadedJobs] = await Promise.all([listProjects(), listJobs()]);
      setProjects(loadedProjects);
      setJobs(loadedJobs);
      if (selectedProject) {
        const refreshed = loadedProjects.find((project) => project.id === selectedProject.id);
        if (refreshed) setSelectedProject(refreshed);
      }
    } catch (error) {
      toast.error(`No se pudo cargar el espacio de trabajo: ${handleAPIError(error)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadProjects();
  }, []);

  useEffect(() => {
    if (!selectedProject) {
      setCatalogs([]);
      return;
    }
    void (async () => {
      try {
        const loadedCatalogs = await listCatalogs(selectedProject.id);
        setCatalogs(loadedCatalogs);
        setJobs(await listJobs(selectedProject.id));
      } catch (error) {
        toast.error(`No se pudieron cargar los catálogos: ${handleAPIError(error)}`);
      }
    })();
  }, [selectedProject]);

  const pendingJobs = useMemo(
    () => jobs.filter((job) => (job.pending_review_count || 0) > 0),
    [jobs]
  );

  const selectCatalog = (catalog: Catalog) => {
    setSelectedCatalogId(catalog.id);
    setCatalogDraft(catalog);
    setCatalogName(catalog.name);
    setMultiLabel(catalog.multi_label);
    setMaxLabels(catalog.max_labels);
    setEntries(catalog.entries.length > 0 ? catalog.entries : [emptyEntry()]);
  };

  const resetCatalogForm = () => {
    setSelectedCatalogId('');
    setCatalogDraft(null);
    setCatalogName('');
    setMultiLabel(false);
    setMaxLabels(1);
    setEntries([emptyEntry()]);
  };

  const saveProject = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectName.trim()) return;
    try {
      const created = await createProject(projectName, projectDescription);
      setProjects((current) => [created, ...current]);
      setSelectedProject(created);
      setProjectName('');
      setProjectDescription('');
      toast.success('Proyecto creado');
    } catch (error) {
      toast.error(`No se pudo crear el proyecto: ${handleAPIError(error)}`);
    }
  };

  const saveCatalog = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedProject || !catalogName.trim()) return;
    setSaving(true);
    try {
      const payload = {
        name: catalogName,
        entries: entries.map((entry) => ({
          ...entry,
          code: entry.code.trim(),
          label: entry.label.trim(),
          description: (entry.description || '').trim(),
          parent_code: entry.parent_code?.trim() || null,
        })),
        multi_label: multiLabel,
        max_labels: multiLabel ? maxLabels : 1,
      };
      const saved = catalogDraft
        ? await updateCatalog(catalogDraft.id, payload)
        : await createCatalog(selectedProject.id, payload);
      setCatalogs((current) => {
        const withoutCurrent = current.filter((catalog) => catalog.id !== saved.id);
        return [saved, ...withoutCurrent];
      });
      selectCatalog(saved);
      toast.success(catalogDraft ? 'Catálogo actualizado' : 'Catálogo creado');
    } catch (error) {
      toast.error(`Catálogo inválido: ${handleAPIError(error)}`);
    } finally {
      setSaving(false);
    }
  };

  const updateEntry = (index: number, changes: Partial<CatalogEntry>) => {
    setEntries((current) => current.map((entry, entryIndex) => (
      entryIndex === index ? { ...entry, ...changes } : entry
    )));
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">Gestión</p>
            <h1 className="text-3xl font-bold text-slate-900">Proyectos, catálogos y trabajos</h1>
            <p className="text-slate-600 mt-1">Guarda configuraciones y revisa ejecuciones sin depender de una sesión temporal.</p>
          </div>
          <button onClick={onBack} className="btn-secondary">Volver</button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr] gap-6">
          <aside className="card h-fit">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-slate-800">Proyectos</h2>
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">{projects.length}</span>
            </div>
            <div className="space-y-2 mb-5">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => setSelectedProject(project)}
                  className={`w-full text-left p-3 rounded-lg border transition ${selectedProject?.id === project.id ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-blue-300'}`}
                >
                  <div className="font-semibold text-slate-800 truncate">{project.name}</div>
                  <div className="text-xs text-slate-500 mt-1">{project.catalog_count || 0} catálogos · {project.job_count || 0} trabajos</div>
                </button>
              ))}
              {!loading && projects.length === 0 && <p className="text-sm text-slate-500">Todavía no hay proyectos.</p>}
            </div>
            <form onSubmit={saveProject} className="border-t pt-4 space-y-2">
              <h3 className="text-sm font-semibold text-slate-700">Nuevo proyecto</h3>
              <input className="input-field" placeholder="Nombre" value={projectName} onChange={(event) => setProjectName(event.target.value)} />
              <textarea className="input-field text-sm" rows={2} placeholder="Descripción (opcional)" value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} />
              <button className="btn-primary w-full" disabled={!projectName.trim()}>Crear proyecto</button>
            </form>
          </aside>

          <main className="space-y-6">
            {!selectedProject ? (
              <div className="card text-center py-16">
                <h2 className="text-xl font-bold text-slate-800">Selecciona o crea un proyecto</h2>
                <p className="text-slate-500 mt-2">Aquí administrarás su catálogo y revisarás sus ejecuciones.</p>
              </div>
            ) : (
              <>
                <div className="card flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div>
                    <p className="text-sm text-slate-500">Proyecto activo</p>
                    <h2 className="text-2xl font-bold text-slate-900">{selectedProject.name}</h2>
                    {selectedProject.description && <p className="text-slate-600 mt-1">{selectedProject.description}</p>}
                  </div>
                  <button onClick={() => onUseProject(selectedProject.id, selectedCatalogId || undefined)} className="btn-primary whitespace-nowrap">
                    Usar para codificar
                  </button>
                </div>

                <section className="card">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-bold text-slate-800">Catálogo de códigos</h2>
                      <p className="text-sm text-slate-500">Los códigos son definidos por cada encuesta; 77, 88 y 99 se conservan como estados especiales.</p>
                    </div>
                    <button onClick={resetCatalogForm} className="text-sm text-blue-600 hover:underline">Nuevo catálogo</button>
                  </div>
                  <div className="flex flex-wrap gap-2 mb-5">
                    {catalogs.map((catalog) => (
                      <button key={catalog.id} onClick={() => selectCatalog(catalog)} className={`px-3 py-2 rounded-lg border text-sm ${selectedCatalogId === catalog.id ? 'border-blue-500 bg-blue-50 text-blue-800' : 'border-slate-200 text-slate-700'}`}>
                        {catalog.name} <span className="text-xs text-slate-500">v{catalog.version}</span>
                      </button>
                    ))}
                    {catalogs.length === 0 && <span className="text-sm text-slate-500">No hay catálogos guardados.</span>}
                  </div>
                  <form onSubmit={saveCatalog} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-3 items-end">
                      <label className="label">Nombre del catálogo<input className="input-field mt-1" value={catalogName} onChange={(event) => setCatalogName(event.target.value)} placeholder="Ej. Problemas principales v1" /></label>
                      <label className="flex items-center gap-2 text-sm text-slate-700 pb-2"><input type="checkbox" checked={multiLabel} onChange={(event) => setMultiLabel(event.target.checked)} /> Multi-label</label>
                      <label className="label">Máximo<input className="input-field mt-1 w-24" type="number" min={1} value={maxLabels} disabled={!multiLabel} onChange={(event) => setMaxLabels(Number(event.target.value) || 1)} /></label>
                    </div>
                    <div className="overflow-x-auto border rounded-lg">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-100 text-left"><tr><th className="p-2">Código</th><th className="p-2">Etiqueta</th><th className="p-2">Descripción</th><th className="p-2">Padre</th><th className="p-2" /></tr></thead>
                        <tbody>
                          {entries.map((entry, index) => (
                            <tr key={`${index}-${entry.code}`} className="border-t">
                              <td className="p-2"><input className="input-field min-w-24" value={entry.code} onChange={(event) => updateEntry(index, { code: event.target.value })} placeholder="01" /></td>
                              <td className="p-2"><input className="input-field min-w-40" value={entry.label} onChange={(event) => updateEntry(index, { label: event.target.value })} placeholder="Etiqueta" /></td>
                              <td className="p-2"><input className="input-field min-w-56" value={entry.description || ''} onChange={(event) => updateEntry(index, { description: event.target.value })} placeholder="Qué incluye" /></td>
                              <td className="p-2"><input className="input-field min-w-24" value={entry.parent_code || ''} onChange={(event) => updateEntry(index, { parent_code: event.target.value })} placeholder="Opcional" /></td>
                              <td className="p-2"><button type="button" onClick={() => setEntries((current) => current.filter((_, entryIndex) => entryIndex !== index))} className="text-red-600 hover:underline" disabled={entries.length === 1}>Quitar</button></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="flex flex-wrap justify-between gap-3">
                      <button type="button" onClick={() => setEntries((current) => [...current, emptyEntry()])} className="btn-secondary">Agregar código</button>
                      <button type="submit" className="btn-primary" disabled={saving || !catalogName.trim()}>{saving ? 'Guardando...' : catalogDraft ? 'Guardar nueva versión' : 'Guardar catálogo'}</button>
                    </div>
                  </form>
                </section>

                <section className="card">
                  <div className="flex items-center justify-between mb-4">
                    <div><h2 className="text-xl font-bold text-slate-800">Trabajos recientes</h2><p className="text-sm text-slate-500">Cada ejecución conserva estado, progreso y casos pendientes.</p></div>
                    {pendingJobs.length > 0 && <span className="text-sm bg-amber-100 text-amber-800 px-3 py-1 rounded-full">{pendingJobs.length} con revisión</span>}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm"><thead className="bg-slate-100 text-left"><tr><th className="p-3">Trabajo</th><th className="p-3">Estado</th><th className="p-3">Progreso</th><th className="p-3">Revisión</th><th className="p-3" /></tr></thead>
                      <tbody>{jobs.map((job) => <tr key={job.id} className="border-t"><td className="p-3"><div className="font-medium">{job.name}</div><div className="text-xs text-slate-500">{new Date(job.created_at).toLocaleString()}</div></td><td className="p-3"><span className="px-2 py-1 rounded-full bg-slate-100">{job.status}</span></td><td className="p-3">{Math.round(job.progress * 100)}% ({job.processed_records}/{job.total_records || '?'})</td><td className="p-3">{job.pending_review_count || 0} pendientes</td><td className="p-3">{(job.review_count || 0) > 0 && <button onClick={() => onOpenJob(job.id)} className="text-blue-600 font-semibold hover:underline">Abrir revisión</button>}</td></tr>)}</tbody>
                    </table>
                    {jobs.length === 0 && <p className="text-sm text-slate-500 py-5 text-center">Todavía no hay trabajos para este proyecto.</p>}
                  </div>
                </section>
              </>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default Workspace;
