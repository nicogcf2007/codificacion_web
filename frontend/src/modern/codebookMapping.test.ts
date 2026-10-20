import { expect, it } from "vitest";
import { suggestCatalog } from "./codebookMapping";

const catalog = { key: "sheet-cp33", sheet: "Codificación", field_id: "CP33T", question_number: "33", question_text: "Pregunta sintética", categories: [{ code: "01", label: "Opción sintética" }], compatible: true, issues: [], candidate_columns: ["CP33T", "P33T"] };

it("only suggests a unique compatible full candidate identifier, never a prefix or question number", () => {
  expect(suggestCatalog("P33T", [catalog])).toBe(catalog.key);
  expect(suggestCatalog("CP33T", [catalog])).toBe(catalog.key);
  expect(suggestCatalog("P3", [catalog])).toBe("");
  expect(suggestCatalog("33", [catalog])).toBe("");
  expect(suggestCatalog("p33t", [catalog])).toBe("");
  expect(suggestCatalog("P33T", [catalog, { ...catalog, key: "conflict" }])).toBe("");
  expect(suggestCatalog("P33T", [{ ...catalog, compatible: false, issues: ["Código 001 incompatible"] }])).toBe("");
});
