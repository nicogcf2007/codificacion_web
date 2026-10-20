import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Upload } from "./Upload";

afterEach(cleanup);

it("separates the Excel codebook picker from the response-base picker and rejects csv", async () => {
  const upload = vi.fn().mockResolvedValue(undefined);
  render(<Upload kind="codebook" onUpload={upload} />);
  const input = screen.getByLabelText("Subir libro de códigos") as HTMLInputElement;
  expect(input.accept).toBe(".xlsx,.xls");
  expect(screen.getByRole("button", { name: "Seleccionar libro de códigos" }).tabIndex).toBe(0);
  fireEvent.change(input, { target: { files: [new File(["synthetic"], "catalogo.csv")] } });
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Selecciona un libro de códigos .xlsx o .xls.");
  expect(upload).not.toHaveBeenCalled();
  const file = new File(["synthetic workbook"], "catalogo.XLS");
  fireEvent.change(input, { target: { files: [file] } });
  await screen.findByText("Carga completada: catalogo.XLS");
  expect(upload).toHaveBeenCalledWith(file);
  expect(input.value).toBe("");
});
