import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
} from "@testing-library/react";
import { ReviewInbox } from "./Review";
import { api } from "./api";
import type { Job, CodedRecord } from "./types";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const job: Job = {
  id: "j",
  project_id: "p",
  survey_id: "s",
  name: "Sintético",
  status: "COMPLETED",
  progress: 100,
  total_records: 1,
  processed_records: 1,
  provider_mode: "demo",
  pause_reason: null,
  created_at: "",
  updated_at: "",
  metrics: {
    api_calls: 1,
    saved_calls: 0,
    savings_pct: 0,
    cost_usd: 0,
    saved_usd: 0,
    purity: null,
    records_per_second: 1,
    eta_seconds: 0,
    input_tokens: 0,
    output_tokens: 0,
  },
  questions: [
    {
      id: "q",
      column_name: "P3",
      question_text: "¿Por qué?",
      codebook_id: "b",
      categories: [
        { code: "01", label: "Créditos" },
        { code: "02", label: "Atención" },
      ],
      max_labels: 1,
    },
  ],
};
const record: CodedRecord = {
  id: "r",
  job_id: "j",
  question_id: "q",
  response_id: 0,
  column_name: "P3",
  text_original: "una idea nueva",
  codes: ["77"],
  confidence: null,
  was_grouped: false,
  prototype_id: "proto",
  review_status: "PENDING",
  review_reason: "Código 77",
};
it("shows functional review reasons without exposing saved model diagnostics", () => {
  render(<ReviewInbox job={job} records={[{ ...record, review_reason: "Salida inválida del modelo" }]} totalPending={1} onRefresh={vi.fn()} report={vi.fn()} />);
  expect(screen.getAllByText("Asignación inválida: requiere revisión humana.")).toHaveLength(2);
  expect(screen.queryAllByText(/modelo|OpenAI|proveedor|motor/i)).toHaveLength(0);
});
it("numeric shortcut selects a category and Enter persists the decision", async () => {
  const request = vi
    .spyOn(api, "request")
    .mockResolvedValue({ ...record, codes: ["02"], review_status: "APPROVED" });
  const refresh = vi.fn().mockResolvedValue(undefined);
  render(
    <ReviewInbox
      job={job}
      records={[record]}
      totalPending={1}
      onRefresh={refresh}
      report={vi.fn()}
    />,
  );
  expect(
    screen.getByText("una idea nueva", { selector: "blockquote" }),
  ).toBeTruthy();
  expect(screen.getByText("Datos de demostración; no usar como resultados reales")).toBeTruthy();
  expect(screen.getByText("Confianza no disponible")).toBeTruthy();
  expect(screen.queryAllByText(/motor|OpenAI|API conectada|IA bloqueada|gpt-/i)).toHaveLength(0);
  fireEvent.keyDown(window, { key: "2" });
  fireEvent.keyDown(window, { key: "Enter" });
  await waitFor(() => expect(request).toHaveBeenCalled());
  expect(request.mock.calls[0][0]).toBe("/jobs/j/records/r");
  expect(JSON.parse(String(request.mock.calls[0][1]?.body)).codes).toEqual([
    "02",
  ]);
  await waitFor(() => expect(refresh).toHaveBeenCalled());
});
it("does not intercept typing in editable fields", () => {
  const request = vi.spyOn(api, "request");
  render(
    <ReviewInbox
      job={job}
      records={[record]}
      totalPending={1}
      onRefresh={vi.fn()}
      report={vi.fn()}
    />,
  );
  const input = document.createElement("input");
  document.body.append(input);
  fireEvent.keyDown(input, { key: "Enter" });
  expect(request).not.toHaveBeenCalled();
  input.remove();
});
