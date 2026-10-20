import { afterEach, it, expect, vi } from "vitest";
import {
  cleanup,
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { Monitor } from "./Monitor";
import { api } from "./api";
import type { Job } from "./types";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const base: Job = {
  id: "j",
  project_id: "p",
  survey_id: "s",
  name: "Sintético",
  status: "PENDING",
  progress: 0,
  total_records: 1,
  processed_records: 0,
  provider_mode: "blocked",
  pause_reason: null,
  created_at: "",
  updated_at: "",
  questions: [],
  metrics: {
    api_calls: 0,
    saved_calls: 0,
    savings_pct: 0,
    cost_usd: null,
    saved_usd: null,
    purity: null,
    records_per_second: 0,
    eta_seconds: null,
    input_tokens: 0,
    output_tokens: 0,
  },
};
it("blocked mode disables the action and never calls the provider", async () => {
  vi.spyOn(api, "observe").mockImplementation(async (_id, onSnapshot) => {
    onSnapshot({ job: base, records: [] });
  });
  const post = vi.spyOn(api, "post");
  render(
    <Monitor
      job={base}
      onUpdated={vi.fn()}
      onReview={vi.fn()}
      onAnalytics={vi.fn()}
      report={vi.fn()}
    />,
  );
  const start = screen.getByRole("button", { name: "Iniciar codificación" });
  expect((start as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(start);
  expect(post).not.toHaveBeenCalled();
  await waitFor(() =>
    expect(screen.getByText("Resultados guardados")).toBeTruthy(),
  );
  expect(screen.getByText("Ejecución no disponible. Contacta al administrador")).toBeTruthy();
  expect(screen.queryAllByText(/motor|modelo|proveedor|OpenAI|\b(?:SSE|REST|API)\b|gpt-|tokens/i)).toHaveLength(0);
});
it("demo assignments are labelled neutrally and retain functional job controls", async () => {
  const job = { ...base, provider_mode: "demo" as const };
  vi.spyOn(api, "observe").mockImplementation(async (_id, onSnapshot) => onSnapshot({ job, records: [] }));
  render(<Monitor job={job} onUpdated={vi.fn()} onReview={vi.fn()} onAnalytics={vi.fn()} report={vi.fn()} />);
  await screen.findByText("Datos de demostración; no usar como resultados reales");
  expect((screen.getByRole("button", { name: "Iniciar codificación" }) as HTMLButtonElement).disabled).toBe(false);
  expect(screen.queryAllByText(/OpenAI|proveedor|modelo|motor|gpt-/i)).toHaveLength(0);
});
it("blocked server availability disables even a previously saved demo execution", async () => {
  const job = { ...base, provider_mode: "demo" as const };
  vi.spyOn(api, "observe").mockImplementation(async (_id, onSnapshot) => onSnapshot({ job, records: [] }));
  const post = vi.spyOn(api, "post");
  render(<Monitor job={job} executionUnavailable onUpdated={vi.fn()} onReview={vi.fn()} onAnalytics={vi.fn()} report={vi.fn()} />);
  const start = screen.getByRole("button", { name: "Iniciar codificación" });
  expect((start as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(start);
  expect(post).not.toHaveBeenCalled();
});
it("completed work shows persisted activity, not a false running indicator", async () => {
  const job = {
    ...base,
    status: "COMPLETED" as const,
    progress: 100,
    processed_records: 1,
  };
  vi.spyOn(api, "observe").mockImplementation(async (_id, onSnapshot) => {
    onSnapshot({ job, records: [] });
  });
  render(
    <Monitor
      job={job}
      onUpdated={vi.fn()}
      onReview={vi.fn()}
      onAnalytics={vi.fn()}
      report={vi.fn()}
    />,
  );
  await waitFor(() =>
    expect(screen.getByText("Resultados guardados")).toBeTruthy(),
  );
  expect(screen.getByText("Ejecución no disponible. Contacta al administrador")).toBeTruthy();
  expect(screen.queryAllByText(/motor|modelo|proveedor|OpenAI|\b(?:SSE|REST|API)\b|gpt-|tokens/i)).toHaveLength(0);
  expect(screen.getByText("Guardado")).toBeTruthy();
  expect(screen.queryByText("En vivo")).toBeNull();
  expect(
    screen.queryByRole("button", { name: "Iniciar codificación" }),
  ).toBeNull();
});
