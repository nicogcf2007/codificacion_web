import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import Console from "./Console";

const standard = { id: "u", email: "analista@example.test", name: "Ana Prueba", role: "STANDARD", active: true, must_change_password: false, created_at: "2026-01-01" };
const project = { id: "p", name: "Estudio privado sintético", client: "Cliente ficticio", status: "ACTIVE", created_at: "2026-01-01", survey_count: 0, job_count: 0 };
function mockApi(user: typeof standard | null = null) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("/api/v1", "");
    let data: unknown;
    let status = 200;
    if (path === "/auth/me") { data = user ? { user, csrf_token: "response-token-not-to-store" } : { detail: "Acceso denegado" }; status = user ? 200 : 401; }
    else if (path === "/auth/login" && init?.method === "POST") { user = standard; data = { user, csrf_token: "response-token-not-to-store" }; }
    else if (path === "/auth/logout") { user = null; data = { ok: true }; }
    else if (path === "/health") data = { status: "ok", provider_mode: "blocked", database: "sqlite", auth_required: true };
    else if (path === "/projects") data = { projects: [project] };
    else if (path === "/jobs") data = { jobs: [] };
    else throw new Error(`Unexpected test route ${path}`);
    return new Response(JSON.stringify(data), { status });
  });
}
beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("scrollTo", vi.fn());
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); localStorage.clear(); });

it("a first visit without cookies prompts for login without falsely announcing an expired session", async () => {
  vi.stubGlobal("fetch", mockApi());
  render(<Console />);
  await screen.findByRole("heading", { name: "Iniciar sesión" });
  expect(screen.queryByText("Tu sesión ha finalizado. Inicia sesión de nuevo.")).toBeNull();
});

it("requires login before loading projects and ties the profile to the real session user", async () => {
  const fetcher = mockApi();
  vi.stubGlobal("fetch", fetcher);
  render(<Console />);
  await screen.findByRole("heading", { name: "Iniciar sesión" });
  expect(fetcher.mock.calls.some(([url]) => url === "/api/v1/projects")).toBe(false);
  expect(screen.queryByText(/registrarse|crear cuenta/i)).toBeNull();
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: standard.email } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "Synthetic-pass-01!" } });
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByText(project.name);
  expect(fetcher.mock.calls.find(([url]) => url === "/api/v1/auth/login")?.[1]?.body).toBe(JSON.stringify({ email: standard.email, password: "Synthetic-pass-01!" }));
  expect(screen.getByRole("button", { name: /Perfil de Ana Prueba/ })).toBeTruthy();
  expect(screen.getByText("AP")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Usuarios" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Auditoría global" })).toBeNull();
  expect(screen.queryByText(/Conexión y ajustes|gpt-|proveedor|OpenAI|API conectada|motor|sqlite/i)).toBeNull();
  expect(screen.getByRole("button", { name: "Actualizar espacio" })).toBeTruthy();
  expect(Object.keys(localStorage)).toEqual(["cnc-theme"]);
});

it("discards private project and job state when a request returns 401", async () => {
  const fetcher = mockApi(standard);
  vi.stubGlobal("fetch", fetcher);
  render(<Console />);
  await screen.findByText(project.name);
  fetcher.mockImplementationOnce(async () => new Response(JSON.stringify({ detail: "Expired" }), { status: 401 }));
  fireEvent.click(screen.getByRole("button", { name: "Actualizar espacio" }));
  await screen.findByRole("heading", { name: "Iniciar sesión" });
  expect(screen.queryByText(project.name)).toBeNull();
  expect(screen.queryByRole("button", { name: /Perfil/ })).toBeNull();
});

it("locks projects behind the mandatory provisional password change", async () => {
  let user = { ...standard, must_change_password: true };
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    let data: unknown;
    if (url === "/api/v1/auth/me") data = { user, csrf_token: "unused-response-token" };
    else if (url === "/api/v1/auth/password") {
      expect(JSON.parse(String(init?.body))).toEqual({ current_password: "Temporary-fixture-01!", password: "Permanent-fixture-02!" });
      user = { ...user, must_change_password: false };
      data = { user, csrf_token: "unused-rotated-token" };
    } else if (url === "/api/v1/health") data = { provider_mode: "blocked" };
    else if (url === "/api/v1/projects") data = { projects: [project] };
    else if (url === "/api/v1/jobs") data = { jobs: [] };
    else throw new Error(`Unexpected route ${url}`);
    return new Response(JSON.stringify(data), { status: 200 });
  });
  vi.stubGlobal("fetch", fetcher);
  render(<Console />);
  await screen.findByRole("heading", { name: "Cambia tu contraseña provisional" });
  expect(fetcher.mock.calls.some(([url]) => url === "/api/v1/projects")).toBe(false);
  fireEvent.change(screen.getByLabelText("Contraseña actual"), { target: { value: "Temporary-fixture-01!" } });
  fireEvent.change(screen.getByLabelText("Nueva contraseña"), { target: { value: "Permanent-fixture-02!" } });
  fireEvent.change(screen.getByLabelText("Confirmar nueva contraseña"), { target: { value: "Mismatch-fixture-03!" } });
  expect((screen.getByRole("button", { name: "Guardar contraseña" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Confirmar nueva contraseña"), { target: { value: "Permanent-fixture-02!" } });
  fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
  await screen.findByText(project.name);
  expect(fetcher.mock.calls.filter(([url]) => url === "/api/v1/auth/me")).toHaveLength(2);
});

it("native submit cannot bypass the new password length or reuse restriction", async () => {
  const user = { ...standard, must_change_password: true };
  const fetcher = mockApi(user);
  vi.stubGlobal("fetch", fetcher);
  render(<Console />);
  await screen.findByRole("heading", { name: "Cambia tu contraseña provisional" });
  fireEvent.change(screen.getByLabelText("Contraseña actual"), { target: { value: "Old-fixture-password" } });
  fireEvent.change(screen.getByLabelText("Nueva contraseña"), { target: { value: "short" } });
  fireEvent.change(screen.getByLabelText("Confirmar nueva contraseña"), { target: { value: "short" } });
  fireEvent.submit(screen.getByLabelText("Nueva contraseña").closest("form")!);
  await waitFor(() => expect(fetcher.mock.calls.filter(([url]) => url === "/api/v1/auth/password")).toHaveLength(0));
  fireEvent.change(screen.getByLabelText("Nueva contraseña"), { target: { value: "Old-fixture-password" } });
  fireEvent.change(screen.getByLabelText("Confirmar nueva contraseña"), { target: { value: "Old-fixture-password" } });
  fireEvent.submit(screen.getByLabelText("Nueva contraseña").closest("form")!);
  expect(fetcher.mock.calls.filter(([url]) => url === "/api/v1/auth/password")).toHaveLength(0);
});

it("logs out using the session endpoint and removes the entire workspace", async () => {
  const fetcher = mockApi(standard);
  vi.stubGlobal("fetch", fetcher);
  render(<Console />);
  await screen.findByText(project.name);
  fireEvent.click(screen.getByRole("button", { name: /Perfil de Ana Prueba/ }));
  fireEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  await screen.findByRole("heading", { name: "Iniciar sesión" });
  expect(screen.queryByText(project.name)).toBeNull();
  expect(fetcher.mock.calls.find(([url]) => url === "/api/v1/auth/logout")?.[1]?.credentials).toBe("include");
});

it("keeps a saved demo job unavailable when the server disables execution without disclosing configuration", async () => {
  const normal = mockApi(standard);
  const job = { id: "j", project_id: "p", survey_id: "s", name: "Plan sintético", status: "PENDING", progress: 0, total_records: 2, processed_records: 0, provider_mode: "demo", pause_reason: null, created_at: "2026-01-01", updated_at: "2026-01-01", questions: [], metrics: { api_calls: 0, saved_calls: 0, savings_pct: 0, cost_usd: null, saved_usd: null, purity: null, records_per_second: 0, eta_seconds: null, input_tokens: 0, output_tokens: 0 } };
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/api/v1/jobs") return new Response(JSON.stringify({ jobs: [job] }));
    if (url.endsWith("/events")) return new Response(`data: ${JSON.stringify({ job, records: [] })}\n\n`, { headers: { "Content-Type": "text/event-stream" } });
    return normal(url, init);
  });
  vi.stubGlobal("fetch", fetcher);
  render(<Console />);
  await screen.findByText(project.name);
  fireEvent.click(screen.getByRole("button", { name: "Ejecuciones" }));
  fireEvent.click(screen.getByRole("button", { name: "Abrir" }));
  await screen.findByText("Resultados guardados");
  expect((screen.getByRole("button", { name: "Iniciar codificación" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("Ejecución no disponible. Contacta al administrador")).toBeTruthy();
  expect(screen.getByText("Datos de demostración; no usar como resultados reales")).toBeTruthy();
  expect(screen.queryAllByText(/OpenAI|proveedor|modelo|motor|API conectada|IA bloqueada/i)).toHaveLength(0);
});

it("login defaults dark on a light system and retains only the theme across login and logout", async () => {
  const fetcher = mockApi();
  vi.stubGlobal("fetch", fetcher);
  render(<Console />);
  await screen.findByRole("heading", { name: "Iniciar sesión" });
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.click(screen.getByRole("button", { name: "Tema claro" }));
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: standard.email } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "Synthetic-pass-01!" } });
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByText(project.name);
  expect(document.documentElement.dataset.theme).toBe("light");
  fireEvent.click(screen.getByRole("button", { name: /Perfil de Ana Prueba/ }));
  fireEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  await screen.findByRole("heading", { name: "Iniciar sesión" });
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(Object.keys(localStorage)).toEqual(["cnc-theme"]);
  expect(localStorage.getItem("cnc-theme")).toBe("light");
});

it("starts dark even on a light system and persists only an explicit light or dark choice", async () => {
  vi.stubGlobal("fetch", mockApi(standard));
  localStorage.setItem("cnc-theme", "system");
  render(<Console />);
  await screen.findByText(project.name);
  await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
  expect(screen.queryByRole("button", { name: "Tema automático" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Tema claro" }));
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(localStorage.getItem("cnc-theme")).toBe("light");
  fireEvent.click(screen.getByRole("button", { name: "Tema oscuro" }));
  expect(localStorage.getItem("cnc-theme")).toBe("dark");
});
