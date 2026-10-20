import type { CodebookCatalog } from "./types";

/** Candidate identifiers are supplied by the server; never infer ranges or numbers. */
export function suggestCatalog(column: string, catalogs: CodebookCatalog[]): string {
  const matches = catalogs.filter((catalog) => catalog.candidate_columns.includes(column));
  return matches.length === 1 && matches[0].compatible ? matches[0].key : "";
}
