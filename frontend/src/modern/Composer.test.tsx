import type { MockInstance } from "vitest";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Composer } from "./Composer";
import { api } from "./api";
import type { Project, Survey, Codebook, CodebookPreview } from "./types";

const project: Project = { id: "p", name: "Carga sintética", client: "Ficticio", status: "ACTIVE", created_at: "", survey_count: 0, job_count: 0 };
const survey: Survey = { id: "s", project_id: "p", filename: "sintetico.xls", total_records: 2, columns: ["P1"], preview: [], created_at: "" };
let request: MockInstance<typeof api.request>;
beforeEach(() => {
  request = vi.spyOn(api, "request").mockImplementation(async (path, init) => init?.method === "POST" ? survey : path.endsWith("codebooks") ? { codebooks: [] } : { surveys: [] });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
function mount() { render(<Composer project={project} onCreated={vi.fn()} report={vi.fn()} />); }

it("offers a visible keyboard-accessible upload button and accepts xls twice including the same file", async () => {
  mount();
  const button = screen.getByRole("button", { name: "Seleccionar archivo" });
  expect(button.tabIndex).toBe(0);
  expect(screen.getByText(".xlsx, .xls o .csv · hasta 50 MB")).toBeTruthy();
  const input = screen.getByLabelText("Subir base de respuestas") as HTMLInputElement;
  expect(input.accept).toBe(".xlsx,.xls,.csv");
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  request.mockResolvedValue(survey);
  const file = new File(["synthetic"], "sintetico.xls", { type: "application/vnd.ms-excel" });
  fireEvent.change(input, { target: { files: [file] } });
  await screen.findByText("Carga completada: sintetico.xls");
  fireEvent.change(input, { target: { files: [file] } });
  await waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(2));
  expect(input.value).toBe("");
});

it("rejects unsupported extensions and files above 50 MB before making an upload request", async () => {
  mount();
  const input = screen.getByLabelText("Subir base de respuestas");
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  fireEvent.change(input, { target: { files: [new File(["not accepted"], "sintetico.txt")] } });
  await screen.findByRole("alert");
  expect(screen.getByText("Selecciona un archivo .xlsx, .xls o .csv.")).toBeTruthy();
  const large = new File(["synthetic"], "grande.xlsx");
  Object.defineProperty(large, "size", { value: 50 * 1024 * 1024 + 1 });
  fireEvent.change(input, { target: { files: [large] } });
  expect(screen.getByText("El archivo supera el límite de 50 MB.")).toBeTruthy();
  expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
});

it("accepts drag-and-drop and shows an indeterminate progress state without invented percentages", async () => {
  mount();
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  let resolveUpload: (value: Survey) => void = () => {};
  request.mockImplementation(() => new Promise<Survey>((resolve) => { resolveUpload = resolve; }));
  const file = new File(["a,b"], "sintetico.csv", { type: "text/csv" });
  const zone = screen.getByRole("region", { name: "Carga de base de respuestas" });
  fireEvent.drop(zone, { dataTransfer: { files: [file], types: ["Files"] } });
  expect(screen.getByRole("progressbar", { name: "Carga de sintetico.csv" }).getAttribute("aria-valuenow")).toBeNull();
  resolveUpload({ ...survey, filename: file.name });
  await screen.findByText("Carga completada: sintetico.csv");
});

it("shows upload errors, leaves saved data unchanged, and accepts retrying the same file", async () => {
  mount();
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  request.mockRejectedValueOnce(new Error("No se pudo leer el archivo. Verifica su contenido."));
  const file = new File(["synthetic"], "sintetico.xlsx");
  const input = screen.getByLabelText("Subir base de respuestas") as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file] } });
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "No se pudo leer el archivo. Verifica su contenido.");
  expect(screen.queryByText("Carga completada: sintetico.xlsx")).toBeNull();
  expect((screen.getByRole("button", { name: "Seleccionar archivo" }) as HTMLButtonElement).disabled).toBe(false);
  fireEvent.change(input, { target: { files: [file] } });
  await screen.findByText("Carga completada: sintetico.xlsx");
  expect(screen.queryByRole("alert")).toBeNull();
  expect(input.value).toBe("");
});

it("rejects empty or multiple files and preserves the visible accessible file picker", async () => {
  mount();
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  const input = screen.getByLabelText("Subir base de respuestas");
  fireEvent.change(input, { target: { files: [new File([], "vacio.csv")] } });
  expect(screen.getByText("El archivo está vacío.")).toBeTruthy();
  const zone = screen.getByRole("region", { name: "Carga de base de respuestas" });
  fireEvent.drop(zone, { dataTransfer: { files: [new File(["a"], "primero.csv"), new File(["b"], "segundo.csv")] } });
  expect(screen.getByText("Selecciona un solo archivo a la vez.")).toBeTruthy();
  const click = vi.spyOn(input, "click");
  fireEvent.click(screen.getByRole("button", { name: "Seleccionar archivo" }));
  expect(click).toHaveBeenCalledOnce();
  expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
});

it("accepts the exact 50 MB boundary and uppercase supported extensions", async () => {
  mount();
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  const file = new File(["synthetic"], "exact-limit.XLSX");
  Object.defineProperty(file, "size", { value: 50 * 1024 * 1024 });
  fireEvent.drop(screen.getByRole("region", { name: "Carga de base de respuestas" }), { dataTransfer: { files: [file] } });
  await screen.findByText("Carga completada: exact-limit.XLSX");
  expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
});

it("Composer never exposes internal implementation labels", async () => {
  mount();
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  expect(screen.queryByText(/motor|OpenAI|proveedor|modelo|IA\b|API/i)).toBeNull();
});

const excelSurvey: Survey = { ...survey, columns: ["P3_1", "P3_2", "P33T"] };
const longQuestion = "¿Qué motivos sintéticos describirías para esta elección? ".repeat(8);
const preview: CodebookPreview = {
  filename: "libro-sintetico.xlsx", sheets: ["Codificación"], warnings: [],
  catalogs: [{ key: "cp3", sheet: "Codificación", field_id: "CP3_1-CP3_2", question_number: "3", question_text: longQuestion,
    categories: [{ code: "01", label: "Opción sintética" }], compatible: true, issues: [], candidate_columns: ["CP3_1", "P3_1", "CP3_2", "P3_2"] }],
};
const importedBook: Codebook = { id: "book-imported", project_id: "p", name: "CP3_1-CP3_2", categories: preview.catalogs[0].categories, max_labels: 1, created_at: "" };
function excelRequests(savedBooks: Codebook[] = []) {
  request.mockImplementation(async (path, init) => {
    if (path.endsWith("/preview")) return preview;
    if (path.endsWith("/import")) return { filename: preview.filename, codebooks: [importedBook], mappings: ["P3_1", "P3_2"].map((column_name) => ({ column_name, codebook_id: importedBook.id, question_text: longQuestion })) };
    if (init?.method === "POST") return excelSurvey;
    return path.endsWith("codebooks") ? { codebooks: savedBooks } : { surveys: [excelSurvey] };
  });
}
async function selectExcelBase(columns = ["P3_1", "P3_2"]) {
  await screen.findByRole("option", { name: /sintetico.xls/ });
  fireEvent.change(screen.getByLabelText("O usar una base guardada"), { target: { value: "s" } });
  columns.forEach((column) => fireEvent.click(screen.getByRole("checkbox", { name: column })));
}
async function uploadBook() {
  const file = new File(["synthetic codebook"], preview.filename);
  fireEvent.change(screen.getByLabelText("Subir libro de códigos"), { target: { files: [file] } });
  await screen.findByText(`Carga completada: ${preview.filename}`);
  return file;
}

it("runs base → explicit columns → Excel preview → required confirmation → prepare using the frozen multipart contract", async () => {
  excelRequests();
  const created = vi.fn();
  const post = vi.spyOn(api, "post").mockResolvedValue({ id: "new-job" });
  render(<Composer project={project} onCreated={created} report={vi.fn()} />);
  expect((screen.getByRole("button", { name: "Seleccionar libro de códigos" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getAllByRole("heading", { level: 2 }).map((item) => item.textContent)).toEqual(["Base de respuestas", "Seleccionar columnas", "Libro de códigos", "Confirmar correspondencias", "Preparar ejecución"]);
  await selectExcelBase();
  const file = await uploadBook();
  expect((screen.getByLabelText("Catálogo P3_1") as HTMLSelectElement).value).toBe("cp3");
  expect((screen.getByLabelText("Catálogo P3_2") as HTMLSelectElement).value).toBe("cp3");
  expect(request.mock.calls.filter(([path]) => path.endsWith("/import"))).toHaveLength(0);
  expect((screen.getByRole("button", { name: "Preparar ejecución" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Confirmar correspondencias" }));
  await screen.findByText("Correspondencias confirmadas.");
  const [, init] = request.mock.calls.find(([path]) => path.endsWith("/import"))!;
  const body = init?.body as FormData;
  expect(body.get("file")).toBe(file);
  expect(body.get("survey_id")).toBe("s");
  expect(Array.from(body.keys()).sort()).toEqual(["file", "selections", "survey_id"]);
  expect(JSON.parse(String(body.get("selections")))).toEqual([
    { column_name: "P3_1", catalog_key: "cp3", max_labels: 1 },
    { column_name: "P3_2", catalog_key: "cp3", max_labels: 1 },
  ]);
  expect((screen.getByLabelText("Pregunta P3_1") as HTMLTextAreaElement).value).toBe(longQuestion);
  fireEvent.change(screen.getByLabelText("Pregunta P3_2"), { target: { value: "Pregunta corregida sintética" } });
  fireEvent.click(screen.getByRole("button", { name: "Preparar ejecución" }));
  await waitFor(() => expect(created).toHaveBeenCalledWith({ id: "new-job" }));
  expect(post).toHaveBeenCalledWith("/coding/jobs", {
    survey_id: "s", name: project.name, questions: [
      { column_name: "P3_1", codebook_id: importedBook.id, question_text: longQuestion },
      { column_name: "P3_2", codebook_id: importedBook.id, question_text: "Pregunta corregida sintética" },
    ],
  });
  expect(within(screen.getByRole("region", { name: "Confirmar correspondencias" })).queryByText(/motor|OpenAI|proveedor|modelo|API/i)).toBeNull();
});

it("reuses saved catalogs only by explicit choice and confirmation, without a new file or first-catalog defaults", async () => {
  const stored: Codebook = { ...importedBook, source: { filename: "previo.xlsx", sheet: "Codificación", field_id: "CP3_1-CP3_2", question_number: "3", question_text: longQuestion, target_columns: ["P3_1", "P3_2"], groupings: {} } };
  const historical: Codebook = { ...importedBook, id: "historical", name: "Catálogo histórico", source: null };
  excelRequests([stored, historical]);
  const post = vi.spyOn(api, "post").mockResolvedValue({ id: "saved-job" });
  mount();
  await selectExcelBase();
  fireEvent.click(screen.getByRole("button", { name: "Reutilizar catálogos guardados" }));
  expect((screen.getByLabelText("Catálogo P3_1") as HTMLSelectElement).value).toBe("");
  expect((screen.getByLabelText("Catálogo P3_2") as HTMLSelectElement).value).toBe("");
  expect((screen.getByRole("button", { name: "Confirmar correspondencias" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Catálogo P3_1"), { target: { value: stored.id } });
  fireEvent.change(screen.getByLabelText("Catálogo P3_2"), { target: { value: historical.id } });
  fireEvent.click(screen.getByRole("button", { name: "Confirmar correspondencias" }));
  await screen.findByText("Correspondencias confirmadas.");
  expect((screen.getByLabelText("Pregunta P3_1") as HTMLTextAreaElement).value).toBe(longQuestion);
  expect((screen.getByLabelText("Pregunta P3_2") as HTMLTextAreaElement).value).toBe("");
  expect((screen.getByRole("button", { name: "Preparar ejecución" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Pregunta P3_2"), { target: { value: "Texto sintético requerido" } });
  fireEvent.click(screen.getByRole("button", { name: "Preparar ejecución" }));
  await waitFor(() => expect(post).toHaveBeenCalledOnce());
  expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
});
