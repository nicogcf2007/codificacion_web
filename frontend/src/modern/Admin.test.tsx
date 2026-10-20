import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import Console from "./Console";

const admin = { id: "admin-fixture", email: "admin@example.test", name: "Admin Sintético", role: "ADMIN", active: true, must_change_password: false, created_at: "2026-01-01" };
const member = { ...admin, id: "new-fixture", name: "Nueva Analista", email: "nueva@example.test", role: "STANDARD", must_change_password: true };
let users: typeof admin[];
let fetcher: ReturnType<typeof vi.fn>;
beforeEach(() => {
  users = [admin];
  vi.stubGlobal("scrollTo", vi.fn());
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    let data: unknown;
    if (url === "/api/v1/auth/me") data = { user: admin, csrf_token: "unused-fixture-token" };
    else if (url === "/api/v1/health") data = { provider_mode: "blocked" };
    else if (url === "/api/v1/projects") data = { projects: [] };
    else if (url === "/api/v1/jobs") data = { jobs: [] };
    else if (url === "/api/v1/admin/users" && init?.method === "POST") { users.push(member); data = member; }
    else if (url === "/api/v1/admin/users") data = { users: [...users] };
    else if (url === "/api/v1/admin/overview") data = { projects: 3, jobs: 7, users: 2, active_jobs: 1, completed_jobs: 5 };
    else if (url.startsWith("/api/v1/admin/audit")) data = { events: [{ id: "a", actor_id: "admin-fixture", actor_name: admin.name, actor_email: admin.email, action: "project.create", resource_type: "project", resource_id: "p", project_id: "p", job_id: null, created_at: "2026-01-01" }], total: 51 };
    else throw new Error(`Unexpected route ${url}`);
    return new Response(JSON.stringify(data), { status: 200 });
  });
  vi.stubGlobal("fetch", fetcher);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); localStorage.clear(); });

it("admin creates a provisional account then reads the canonical account list back", async () => {
  render(<Console />);
  fireEvent.click(await screen.findByRole("button", { name: "Usuarios" }));
  await screen.findByRole("columnheader", { name: "Usuario" });
  fireEvent.click(screen.getByRole("button", { name: "Crear usuario" }));
  fireEvent.change(screen.getByLabelText("Nombre completo"), { target: { value: member.name } });
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: member.email } });
  fireEvent.change(screen.getByLabelText("Contraseña inicial"), { target: { value: "Synthetic-pass-012!" } });
  expect((screen.getByLabelText("Exigir cambio de contraseña al entrar") as HTMLInputElement).checked).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Guardar usuario" }));
  await screen.findByText(member.email);
  const creation = fetcher.mock.calls.find(([url, init]) => url === "/api/v1/admin/users" && init?.method === "POST");
  expect(JSON.parse(String(creation?.[1]?.body))).toEqual({ email: member.email, name: member.name, password: "Synthetic-pass-012!", role: "STANDARD", must_change_password: true });
  expect(fetcher.mock.calls.filter(([url, init]) => url === "/api/v1/admin/users" && init?.method !== "POST").length).toBeGreaterThanOrEqual(2);
  expect(screen.queryByLabelText("Contraseña inicial")).toBeNull();
});

it("admin can explicitly assign a definitive password and administrator role", async () => {
  render(<Console />);
  fireEvent.click(await screen.findByRole("button", { name: "Usuarios" }));
  await screen.findByRole("columnheader", { name: "Usuario" });
  fireEvent.click(screen.getByRole("button", { name: "Crear usuario" }));
  fireEvent.change(screen.getByLabelText("Nombre completo"), { target: { value: member.name } });
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: member.email } });
  fireEvent.change(screen.getByLabelText("Contraseña inicial"), { target: { value: "Synthetic-definitive-012!" } });
  fireEvent.change(screen.getByLabelText("Rol"), { target: { value: "ADMIN" } });
  fireEvent.click(screen.getByLabelText("Exigir cambio de contraseña al entrar"));
  expect(screen.getByText(/Definitiva: la persona podrá entrar directamente/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Guardar usuario" }));
  await screen.findByText(member.email);
  const creation = fetcher.mock.calls.find(([url, init]) => url === "/api/v1/admin/users" && init?.method === "POST");
  expect(JSON.parse(String(creation?.[1]?.body))).toEqual({ email: member.email, name: member.name, password: "Synthetic-definitive-012!", role: "ADMIN", must_change_password: false });
  expect(Object.keys(localStorage)).toEqual(["cnc-theme"]);
  expect(screen.queryByLabelText("Contraseña inicial")).toBeNull();
});

it("admin overview shows aggregate database counts and global audit paginates by the server total", async () => {
  render(<Console />);
  fireEvent.click(await screen.findByRole("button", { name: "Resumen administrativo" }));
  await screen.findByText("Trabajos completados");
  expect(screen.getByText("7")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Auditoría global" }));
  await screen.findByText("project.create");
  expect(screen.getByText("51 eventos en total")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Siguiente página" }));
  await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url === "/api/v1/admin/audit?limit=50&offset=50")).toBe(true));
});
