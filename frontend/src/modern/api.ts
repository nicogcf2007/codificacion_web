import type { Snapshot } from "./types";

export class SessionExpired extends Error {
  constructor() {
    super("Tu sesión ha finalizado. Inicia sesión de nuevo.");
    this.name = "SessionExpired";
  }
}

function csrfCookie(): string {
  const value = document.cookie.split(";").map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith("cnc_csrf="))?.slice("cnc_csrf=".length);
  try {
    return value ? decodeURIComponent(value) : "";
  } catch {
    return "";
  }
}

async function checkResponse(response: Response, path = ""): Promise<void> {
  if (response.ok) return;
  if (response.status === 401) {
    if (path !== "/auth/login") window.dispatchEvent(new Event("cnc:session-expired"));
    throw new SessionExpired();
  }
  const data = await response.json().catch(() => null);
  if (response.status === 403) throw new Error("No tienes permiso para esta acción. Contacta al administrador.");
  if (response.status >= 500) throw new Error("Ejecución no disponible. Contacta al administrador.");
  throw new Error(publicError(errorMessage(data)));
}

function publicError(text: string): string {
  return /\b(?:openai|provider|proveedor|modelo?|motor|health|api|token|clave|credencial|coding_provider|app_access_token)\b|gpt-/i.test(text)
    ? "Ejecución no disponible. Contacta al administrador"
    : text;
}

function errorMessage(data: unknown): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
      return detail
        .map((item) =>
          typeof item?.msg === "string" ? item.msg : "Datos inválidos",
        )
        .join(" · ");
  }
  return "No se pudo completar la solicitud";
}

export async function readSnapshots(
  stream: ReadableStream<Uint8Array>,
  onSnapshot: (snapshot: Snapshot) => void,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let complete = false;
  try {
    while (!complete) {
      const { value, done } = await reader.read();
      complete = done;
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      let separator: number;
      while ((separator = buffer.indexOf("\n\n")) >= 0) {
        const event = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        const data = event
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (data) onSnapshot(JSON.parse(data) as Snapshot);
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
}

export class Api {
  constructor(private readonly base = "") {}
  private headers(body?: BodyInit | null, method = "GET"): Headers {
    const headers = new Headers();
    if (["POST", "PATCH", "PUT", "DELETE"].includes(method.toUpperCase())) {
      const csrf = csrfCookie();
      if (csrf) headers.set("X-CSRF-Token", csrf);
    }
    if (body && !(body instanceof FormData))
      headers.set("Content-Type", "application/json");
    return headers;
  }
  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.base}/api/v1${path}`, {
      ...init,
      credentials: "include",
      headers: this.headers(init.body, init.method),
      signal: init.signal ?? AbortSignal.timeout(120000),
    });
    await checkResponse(response, path);
    return response.json() as Promise<T>;
  }
  post<T>(path: string, body: unknown = {}): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }
  async observe(
    id: string,
    onSnapshot: (snapshot: Snapshot) => void,
    signal: AbortSignal,
  ) {
    const response = await fetch(
      `${this.base}/api/v1/jobs/${encodeURIComponent(id)}/events`,
      { credentials: "include", headers: this.headers(), signal },
    );
    await checkResponse(response);
    if (!response.body)
      throw new Error("El navegador no admite transmisión en vivo");
    await readSnapshots(response.body, onSnapshot);
  }
  async download(id: string, format: "csv" | "xlsx") {
    const response = await fetch(
      `${this.base}/api/v1/jobs/${encodeURIComponent(id)}/export?format=${format}`,
      { credentials: "include", headers: this.headers(), signal: AbortSignal.timeout(120000) },
    );
    await checkResponse(response);
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `CNC-${id}.${format}`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
const environment = (
  import.meta as ImportMeta & { env: Record<string, string> }
).env;
export const api = new Api(environment.VITE_API_URL || "");
export const message = (error: unknown) =>
  error instanceof Error ? publicError(error.message) : "No se pudo completar la solicitud";
