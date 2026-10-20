import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Plus, RefreshCw } from "lucide-react";
import { api, message } from "./api";
import { Empty, Metric, Modal, number } from "./ui";
import type { AdminOverview, AuditEvent, User } from "./types";

type AdminView = "users" | "audit" | "overview";

function UsersView({ report }: { report: (error: string) => void }) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<User["role"]>("STANDARD");
  const [provisional, setProvisional] = useState(true);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const reload = useCallback(async () => {
    setLoading(true); setFailed(false);
    try { const data = await api.request<{ users: User[] }>("/admin/users"); setUsers(data.users); return data.users; }
    catch (problem) { setFailed(true); report(message(problem)); throw problem; }
    finally { setLoading(false); }
  }, [report]);
  useEffect(() => { void reload().catch(() => {}); }, [reload]);
  const changeOpen = (value: boolean) => { if (busy) return; setOpen(value); setPassword(""); setFormError(""); };
  return <section className="panel">
    <div className="panel-head wrap"><div><h2>Cuentas del equipo</h2><p>Todos los usuarios activos comparten el espacio de proyectos.</p></div><div className="row"><button className="icon-button" aria-label="Actualizar usuarios" disabled={loading || busy} onClick={() => void reload().catch(() => {})}><RefreshCw size={16} /></button><button className="button primary" onClick={() => changeOpen(true)}><Plus size={15} />Crear usuario</button></div></div>
    {notice && <div className="notice admin-notice" role="status">{notice}</div>}
    {loading ? <div className="empty" role="status">Cargando cuentas…</div> : failed ? <Empty title="No se pudieron cargar las cuentas" description="Usa Actualizar usuarios para volver a intentarlo." /> : <div className="table-scroll"><table><caption className="sr-only">Usuarios del espacio compartido</caption><thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Contraseña</th><th>Creación</th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td><strong>{user.name}</strong><small>{user.email}</small></td><td>{user.role === "ADMIN" ? "Administrador" : "Analista"}</td><td>{user.active ? "Activo" : "Inactivo"}</td><td>{user.must_change_password ? "Cambio obligatorio" : "Personal"}</td><td>{new Date(user.created_at).toLocaleDateString("es-CO")}</td></tr>)}</tbody></table>{!users.length && <Empty title="Sin cuentas para mostrar" description="Crea una cuenta para incorporar a tu equipo." />}</div>}
    <Modal open={open} onOpenChange={changeOpen} title="Crear usuario" description="Asigna una cuenta individual. Entrega la contraseña por un canal seguro; no se mostrará después de guardar.">
      <form className="form-stack" onSubmit={async (event) => {
        event.preventDefault(); if (busy) return; setBusy(true); setFormError(""); setNotice("");
        try {
          const created = await api.post<User>("/admin/users", { email: email.trim(), name: name.trim(), password, role, must_change_password: provisional });
          setPassword("");
          const current = await reload();
          if (!current.some((user) => user.id === created.id)) throw new Error("La cuenta se guardó, pero no se pudo confirmar en la lista. Actualiza las cuentas antes de repetir.");
          setOpen(false); setName(""); setEmail(""); setRole("STANDARD"); setProvisional(true);
          setNotice("Cuenta creada. Comparte las instrucciones de acceso por un canal seguro.");
        } catch (problem) { setFormError(message(problem)); }
        finally { setPassword(""); setBusy(false); }
      }}>
        {formError && <div className="error-banner" role="alert">{formError}</div>}
        <label>Nombre completo<input required maxLength={240} autoComplete="off" value={name} onChange={(event) => setName(event.target.value)} disabled={busy} /></label>
        <label>Correo electrónico<input type="email" required maxLength={254} autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} /></label>
        <label>Rol<select value={role} onChange={(event) => setRole(event.target.value as User["role"])} disabled={busy}><option value="STANDARD">Analista</option><option value="ADMIN">Administrador</option></select></label>
        <label>Contraseña inicial<input type="password" required minLength={12} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} /></label>
        <small className="muted">Mínimo 12 caracteres. No se almacena en este navegador.</small>
        <label className="checkbox-label"><input type="checkbox" checked={provisional} onChange={(event) => setProvisional(event.target.checked)} disabled={busy} />Exigir cambio de contraseña al entrar</label>
        <div className="notice">{provisional ? "Provisional: la persona deberá elegir su contraseña antes de abrir los estudios." : "Definitiva: la persona podrá entrar directamente al espacio compartido."}</div>
        <button className="button primary" disabled={busy || !name.trim() || !email.trim() || password.length < 12}>{busy ? "Guardando…" : "Guardar usuario"}</button>
      </form>
    </Modal>
  </section>;
}

function OverviewView({ report }: { report: (error: string) => void }) {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void api.request<AdminOverview>("/admin/overview", { signal: controller.signal }).then((current) => { if (!controller.signal.aborted) setData(current); }).catch((problem) => { if (!controller.signal.aborted) { setFailed(true); report(message(problem)); } });
    return () => controller.abort();
  }, [report]);
  return <section className="panel form-stack"><div><span className="eyebrow">ESPACIO COMPARTIDO</span><h2>Resumen del equipo</h2><p className="muted">Totales de proyectos y trabajos guardados de todos los usuarios.</p></div>{!data ? <div role="status">{failed ? "Resumen no disponible. Actualiza el espacio para reintentar." : "Cargando resumen…"}</div> : <div className="admin-metrics"><Metric label="Proyectos" value={number(data.projects)} note="Estudios del equipo" /><Metric label="Trabajos" value={number(data.jobs)} note="Ejecuciones guardadas" /><Metric label="Usuarios" value={number(data.users)} note="Cuentas del equipo" /><Metric label="Trabajos activos" value={number(data.active_jobs)} note="En proceso" /><Metric label="Trabajos completados" value={number(data.completed_jobs)} note="Con resultados guardados" /></div>}</section>;
}

function AuditView({ report }: { report: (error: string) => void }) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setFailed(false);
    void api.request<{ events: AuditEvent[]; total: number }>(`/admin/audit?limit=50&offset=${offset}`, { signal: controller.signal }).then((data) => { if (!controller.signal.aborted) { setEvents(data.events); setTotal(data.total); } }).catch((problem) => { if (!controller.signal.aborted) { setFailed(true); setEvents([]); report(message(problem)); } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [offset, report]);
  return <section className="panel"><div className="panel-head"><div><h2>Trazabilidad del equipo</h2><p>Acciones globales atribuidas a la identidad de cada sesión.</p></div><span className="muted">{total} eventos en total</span></div>{loading ? <div className="empty" role="status">Cargando auditoría…</div> : failed ? <Empty title="Auditoría no disponible" description="Actualiza el espacio para volver a intentarlo." /> : events.length ? <div className="table-scroll"><table><caption className="sr-only">Auditoría global del espacio compartido</caption><thead><tr><th>Fecha</th><th>Persona</th><th>Acción</th><th>Recurso</th><th>Proyecto / trabajo</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td>{new Date(event.created_at).toLocaleString("es-CO")}</td><td><strong>{event.actor_name || event.actor_email || "Histórico · sin autor registrado"}</strong>{event.actor_name && event.actor_email && <small>{event.actor_email}</small>}</td><td><code>{event.action}</code></td><td>{event.resource_type}<small>{event.resource_id || "—"}</small></td><td>{event.project_id || "—"}<small>{event.job_id || "—"}</small></td></tr>)}</tbody></table></div> : <Empty title="Sin eventos para mostrar" description="Las acciones de tu equipo aparecerán aquí." />}
    <div className="panel-footer row between wrap"><span>Página {Math.floor(offset / 50) + 1} · {events.length} eventos en esta página</span><div className="row"><button className="button small" aria-label="Página anterior" disabled={loading || offset === 0} onClick={() => setOffset((value) => Math.max(0, value - 50))}><ChevronLeft size={16} />Anterior</button><button className="button small" aria-label="Siguiente página" disabled={loading || failed || offset + 50 >= total} onClick={() => setOffset((value) => value + 50)}>Siguiente<ChevronRight size={16} /></button></div></div>
  </section>;
}

export function AdminPanel({ user, view, report }: { user: User; view: AdminView; report: (error: string) => void }) {
  if (user.role !== "ADMIN") return <Empty title="Acceso restringido" description="Esta sección está disponible solo para administradores." />;
  return view === "users" ? <UsersView report={report} /> : view === "audit" ? <AuditView report={report} /> : <OverviewView report={report} />;
}
