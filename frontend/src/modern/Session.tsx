import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Moon, Sun, LogOut, ChevronDown, KeyRound } from "lucide-react";
import { api, message, SessionExpired } from "./api";
import { Modal } from "./ui";
import type { Session, User } from "./types";

type Theme = "light" | "dark";
const ThemeContext = createContext<{ theme: Theme; setTheme: (theme: Theme) => void }>({ theme: "dark", setTheme: () => {} });

export function ThemeToggle() {
  const { theme, setTheme } = useContext(ThemeContext);
  return <div className="theme-switch" role="group" aria-label="Apariencia">
    <button type="button" className={theme === "light" ? "active" : ""} aria-label="Tema claro" aria-pressed={theme === "light"} onClick={() => setTheme("light")}><Sun size={16} /></button>
    <button type="button" className={theme === "dark" ? "active" : ""} aria-label="Tema oscuro" aria-pressed={theme === "dark"} onClick={() => setTheme("dark")}><Moon size={16} /></button>
  </div>;
}

function Login({ onUser, notice }: { onUser: (user: User) => void; notice: string }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return <main className="cnc-app auth-screen">
    <div className="auth-theme"><ThemeToggle /></div>
    <div className="auth-intro">
      <img src="/cnc.svg" alt="Centro Nacional de Consultoría" className="cnc-logo" />
      <span className="eyebrow">CNC / STUDIO</span>
      <h2>De respuestas abiertas a decisiones trazables.</h2>
      <p>Un espacio compartido para preparar, codificar y revisar tus estudios.</p>
      <span className="auth-caption">Herramientas de investigación · Acceso de equipo</span>
    </div>
    <section className="panel form-stack auth-card">
      <span className="eyebrow">BIENVENIDO A TU ESPACIO</span>
      <h1>Iniciar sesión</h1>
      <p className="muted">Usa la cuenta que te asignó tu administrador.</p>
      {notice && <div role="status" className="notice">{notice}</div>}
      {error && <div role="alert" className="error-banner">{error}</div>}
      <form className="form-stack" onSubmit={async (event) => {
        event.preventDefault();
        if (busy) return;
        setBusy(true);
        setError("");
        try {
          const { user } = await api.post<Session>("/auth/login", { email: email.trim(), password });
          onUser(user);
        } catch (problem) {
          setError(problem instanceof SessionExpired ? "No se pudo iniciar sesión. Verifica tu correo y contraseña." : message(problem));
        } finally {
          setPassword("");
          setBusy(false);
        }
      }}>
        <label>Correo electrónico<input type="email" autoComplete="username" required autoFocus value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} /></label>
        <label>Contraseña<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} /></label>
        <button className="button primary" disabled={busy || !email.trim() || !password}>{busy ? "Entrando…" : "Entrar"}</button>
      </form>
      <small className="muted">¿Necesitas acceso? Contacta al administrador de tu equipo.</small>
    </section>
  </main>;
}

export function PasswordForm({ onUser }: { onUser: (user: User) => void }) {
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return <form className="form-stack" onSubmit={async (event) => {
    event.preventDefault();
    if (busy || !current || password.length < 12 || password.length > 128 || password === current || password !== confirm) return;
    setBusy(true);
    setError("");
    try {
      await api.post<Session>("/auth/password", { current_password: current, password });
      const { user } = await api.request<Session>("/auth/me");
      onUser(user);
    } catch (problem) {
      setError(message(problem));
    } finally {
      setCurrent(""); setPassword(""); setConfirm(""); setBusy(false);
    }
  }}>
    {error && <div role="alert" className="error-banner">{error}</div>}
    <label>Contraseña actual<input type="password" autoComplete="current-password" required value={current} onChange={(event) => setCurrent(event.target.value)} disabled={busy} /></label>
    <label>Nueva contraseña<input type="password" autoComplete="new-password" minLength={12} maxLength={128} required aria-describedby="password-help" value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} /></label>
    <small id="password-help" className="muted">Usa al menos 12 caracteres. Elige una contraseña distinta a la actual.</small>
    <label>Confirmar nueva contraseña<input type="password" autoComplete="new-password" maxLength={128} required value={confirm} onChange={(event) => setConfirm(event.target.value)} disabled={busy} /></label>
    {confirm && password !== confirm && <small role="status" className="field-error">Las contraseñas no coinciden.</small>}
    <button className="button primary" disabled={busy || !current || password.length < 12 || password.length > 128 || password === current || password !== confirm}>{busy ? "Guardando…" : "Guardar contraseña"}</button>
  </form>;
}

export function SessionProfile({ user, onLogout, onUser }: { user: User; onLogout: () => Promise<void>; onUser: (user: User) => void }) {
  const [open, setOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const initials = user.name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toLocaleUpperCase() || user.email[0].toLocaleUpperCase();
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => { if (!ref.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") { setOpen(false); ref.current?.querySelector("button")?.focus(); } };
    window.addEventListener("pointerdown", dismiss); window.addEventListener("keydown", escape);
    return () => { window.removeEventListener("pointerdown", dismiss); window.removeEventListener("keydown", escape); };
  }, [open]);
  return <div className="session-profile" ref={ref}>
    <button className="profile-trigger" aria-label={`Perfil de ${user.name}`} aria-expanded={open} aria-controls="profile-actions" onClick={() => setOpen((value) => !value)}>
      <span className="avatar small" aria-hidden="true">{initials}</span><span className="profile-name">{user.name}</span><ChevronDown size={14} />
    </button>
    {open && <div id="profile-actions" className="profile-popover">
      <strong>{user.name}</strong><small>{user.email}</small><span className="chip">{user.role === "ADMIN" ? "Administrador" : "Analista"}</span>
      <button className="button" onClick={() => { setOpen(false); setPasswordOpen(true); }}><KeyRound size={15} />Cambiar contraseña</button>
      <button className="button" disabled={busy} onClick={async () => { setBusy(true); try { await onLogout(); setOpen(false); } finally { setBusy(false); } }}><LogOut size={15} />{busy ? "Cerrando…" : "Cerrar sesión"}</button>
    </div>}
    <Modal open={passwordOpen} onOpenChange={setPasswordOpen} title="Cambiar contraseña" description="Las otras sesiones se cerrarán al guardar la nueva contraseña.">
      <PasswordForm onUser={(current) => { onUser(current); setPasswordOpen(false); }} />
    </Modal>
  </div>;
}

export function SessionBoundary({ children }: { children: (user: User, onLogout: () => Promise<void>, onUser: (user: User) => void) => ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const hadSession = useRef(false);
  const [checking, setChecking] = useState(true);
  const [notice, setNotice] = useState("");
  const [theme, setTheme] = useState<Theme>(() => {
    try { return localStorage.getItem("cnc-theme") === "light" ? "light" : "dark"; } catch { return "dark"; }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("cnc-theme", theme); } catch { /* Optional appearance preference. */ }
  }, [theme]);
  useEffect(() => {
    const controller = new AbortController();
    const expired = () => { controller.abort(); setUser(null); setChecking(false); if (hadSession.current) setNotice("Tu sesión ha finalizado. Inicia sesión de nuevo."); };
    window.addEventListener("cnc:session-expired", expired);
    void api.request<Session>("/auth/me", { signal: controller.signal }).then(({ user: current }) => {
      if (!controller.signal.aborted) { hadSession.current = true; setUser(current); }
    }).catch((problem) => {
      if (!controller.signal.aborted && !(problem instanceof SessionExpired)) setNotice("No se pudo verificar tu sesión. Intenta iniciar sesión o contacta al administrador.");
    }).finally(() => { if (!controller.signal.aborted) setChecking(false); });
    return () => { controller.abort(); window.removeEventListener("cnc:session-expired", expired); };
  }, []);
  const accept = (current: User) => { hadSession.current = true; setUser(current); setNotice(""); };
  const logout = async () => {
    try { await api.post<{ ok: boolean }>("/auth/logout"); hadSession.current = false; setUser(null); setNotice("Has cerrado sesión."); }
    catch (problem) { if (!(problem instanceof SessionExpired)) setNotice(message(problem)); }
  };
  return <ThemeContext.Provider value={{ theme, setTheme }}>
    {checking ? <main className="cnc-app auth-screen"><div className="empty" role="status">Verificando sesión…</div></main>
      : !user ? <Login onUser={accept} notice={notice} />
      : user.must_change_password ? <main className="cnc-app auth-screen password-screen"><div className="auth-theme"><ThemeToggle /></div><section className="panel form-stack auth-card"><span className="eyebrow">SEGURIDAD DE TU CUENTA</span><h1>Cambia tu contraseña provisional</h1><p className="muted">Hola, {user.name}. Antes de acceder a los estudios, define tu contraseña personal.</p><PasswordForm onUser={accept} /><button className="button" onClick={() => void logout()}>Cerrar sesión</button></section></main>
      : <>{notice && <div className="session-notice notice" role="alert">{notice}</div>}{children(user, logout, accept)}</>}
  </ThemeContext.Provider>;
}
