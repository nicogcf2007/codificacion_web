import { it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { Workspace } from "./Workspace";
afterEach(cleanup);
it("creates a project with its client and prevents empty submission", async () => {
  const create = vi.fn().mockResolvedValue(undefined);
  render(
    <Workspace
      projects={[]}
      loading={false}
      onCreate={create}
      onSelect={vi.fn()}
    />,
  );
  const button = screen.getByRole("button", { name: "Crear proyecto" });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Nombre del estudio"), {
    target: { value: "Mibanco sintético" },
  });
  fireEvent.change(screen.getByLabelText("Cliente"), {
    target: { value: "CNC" },
  });
  fireEvent.click(button);
  expect(create).toHaveBeenCalledWith("Mibanco sintético", "CNC");
});
it("searches real project data without injecting demo projects", () => {
  const project = {
    id: "p",
    name: "Mibanco",
    client: "CNC",
    status: "ACTIVE",
    created_at: "2026-01-01T00:00:00Z",
    survey_count: 2,
    job_count: 3,
  };
  render(
    <Workspace
      projects={[project]}
      loading={false}
      onCreate={vi.fn()}
      onSelect={vi.fn()}
    />,
  );
  expect(screen.getByText("Mibanco")).toBeTruthy();
  fireEvent.change(screen.getByPlaceholderText("Buscar estudio o cliente…"), {
    target: { value: "inexistente" },
  });
  expect(screen.queryByText("Mibanco")).toBeNull();
  expect(screen.getByText("No hay proyectos que coincidan")).toBeTruthy();
});
