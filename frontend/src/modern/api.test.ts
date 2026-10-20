import { describe, it, expect, vi, afterEach } from "vitest";
import { Api, readSnapshots } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "cnc_csrf=; Max-Age=0; path=/";
});

describe("v1 session boundary", () => {
  it("includes cookies and reads the current CSRF cookie for each mutation", async () => {
    const save = vi.fn();
    vi.stubGlobal("localStorage", { setItem: save });
    const fetcher = vi.fn().mockImplementation(async () =>
      new Response(JSON.stringify({ id: "p" }), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetcher);
    const api = new Api("");
    document.cookie = "cnc_csrf=synthetic-csrf; path=/";
    await api.post("/projects", { name: "Estudio", client: "CNC" });
    expect(fetcher.mock.calls[0][0]).toBe("/api/v1/projects");
    expect(fetcher.mock.calls[0][1].credentials).toBe("include");
    const headers = new Headers(fetcher.mock.calls[0][1].headers);
    expect(headers.get("Authorization")).toBeNull();
    expect(headers.get("X-CSRF-Token")).toBe("synthetic-csrf");
    expect(headers.get("Content-Type")).toBe("application/json");
    document.cookie = "cnc_csrf=rotated-csrf; path=/";
    await api.request("/jobs/j/records/r", { method: "PATCH", body: JSON.stringify({ codes: ["01"] }) });
    expect(new Headers(fetcher.mock.calls[1][1].headers).get("X-CSRF-Token")).toBe("rotated-csrf");
    const body = new FormData();
    body.append("file", new Blob(["a,b"]), "synthetic.csv");
    await api.request("/projects/p/surveys", { method: "POST", body });
    expect(new Headers(fetcher.mock.calls[2][1].headers).get("Content-Type")).toBeNull();
    await api.request("/auth/me");
    expect(new Headers(fetcher.mock.calls[3][1].headers).get("X-CSRF-Token")).toBeNull();
    expect(save).not.toHaveBeenCalled();
    expect("setToken" in api).toBe(false);
  });
  it("notifies the session boundary on 401 instead of returning an empty collection", async () => {
    const expired = vi.fn();
    window.addEventListener("cnc:session-expired", expired);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Acceso denegado" }), { status: 401 }),
    ));
    await expect(new Api("").request("/projects")).rejects.toMatchObject({ name: "SessionExpired" });
    expect(expired).toHaveBeenCalledTimes(1);
    window.removeEventListener("cnc:session-expired", expired);
  });
  it("conceals technical errors instead of exposing execution configuration", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "El proveedor OpenAI debe coincidir con el modelo guardado" }), { status: 409 })));
    await expect(new Api("").post("/jobs/j/start")).rejects.toThrow("Ejecución no disponible. Contacta al administrador");
  });
  it("includes session cookies for streaming and downloads, and expires either on 401", async () => {
    const fetcher = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ detail: "Expired" }), { status: 401 }));
    vi.stubGlobal("fetch", fetcher);
    const api = new Api("");
    await expect(api.observe("synthetic", vi.fn(), new AbortController().signal)).rejects.toMatchObject({ name: "SessionExpired" });
    await expect(api.download("synthetic", "xlsx")).rejects.toMatchObject({ name: "SessionExpired" });
    for (const [, init] of fetcher.mock.calls) {
      expect(init.credentials).toBe("include");
      expect(new Headers(init.headers).get("Authorization")).toBeNull();
    }
  });
  it("decodes SSE fragmented across UTF8 chunks", async () => {
    const bytes = new TextEncoder().encode(
      'event: snapshot\r\ndata: {"job":{"name":"Codificación"},"records":[]}\r\n\r\n',
    );
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(bytes.slice(0, 53));
        controller.enqueue(bytes.slice(53));
        controller.close();
      },
    });
    const onSnapshot = vi.fn();
    await readSnapshots(stream, onSnapshot);
    expect(onSnapshot).toHaveBeenCalledTimes(1);
    expect(onSnapshot.mock.calls[0][0].job.name).toBe("Codificación");
  });
});
