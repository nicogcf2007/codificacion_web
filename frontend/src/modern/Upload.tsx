import { useId, useRef, useState } from "react";
import { FileUp, CheckCircle2, AlertCircle } from "lucide-react";
import { message } from "./api";

export function Upload({ onUpload, disabled = false, kind = "survey" }: { onUpload: (file: File) => Promise<void>; disabled?: boolean; kind?: "survey" | "codebook" }) {
  const isBook = kind === "codebook";
  const input = useRef<HTMLInputElement>(null);
  const inFlight = useRef(false);
  const dragDepth = useRef(0);
  const limits = useId();
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [filename, setFilename] = useState("");
  const [error, setError] = useState("");
  const busy = disabled || status === "uploading";
  const select = async (files: FileList | File[]) => {
    if (busy || inFlight.current || !files.length) return;
    const file = files[0];
    setFilename(file.name); setError("");
    let invalid = "";
    if (files.length > 1) invalid = "Selecciona un solo archivo a la vez.";
    else if (!(isBook ? /\.(xlsx|xls)$/i : /\.(xlsx|xls|csv)$/i).test(file.name)) invalid = isBook ? "Selecciona un libro de códigos .xlsx o .xls." : "Selecciona un archivo .xlsx, .xls o .csv.";
    else if (file.size > 50 * 1024 * 1024) invalid = "El archivo supera el límite de 50 MB.";
    else if (!file.size) invalid = "El archivo está vacío.";
    if (invalid) { setError(invalid); setStatus("error"); return; }
    inFlight.current = true; setStatus("uploading");
    try { await onUpload(file); setStatus("success"); }
    catch (problem) { setError(message(problem)); setStatus("error"); }
    finally { inFlight.current = false; }
  };
  return <div className={`upload-zone ${dragging ? "drag-active" : ""}`} role="region" aria-label={isBook ? "Carga de libro de códigos" : "Carga de base de respuestas"} aria-describedby={limits} aria-busy={status === "uploading"}
    onDragEnter={(event) => { event.preventDefault(); if (!busy) { dragDepth.current += 1; setDragging(true); } }}
    onDragLeave={(event) => { event.preventDefault(); dragDepth.current = Math.max(0, dragDepth.current - 1); if (!dragDepth.current) setDragging(false); }}
    onDragOver={(event) => { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = busy ? "none" : "copy"; }}
    onDrop={(event) => { event.preventDefault(); dragDepth.current = 0; setDragging(false); void select(event.dataTransfer.files); }}>
    <FileUp size={28} aria-hidden="true" />
    <strong>{isBook ? "Subir libro de códigos" : "Sube tu base de respuestas"}</strong>
    <p className="muted">Arrastra el archivo aquí o selecciónalo desde tu equipo.</p>
    <span id={limits}>{isBook ? ".xlsx o .xls · hasta 50 MB" : ".xlsx, .xls o .csv · hasta 50 MB"}</span>
    <button type="button" className="button primary" disabled={busy} onClick={() => { if (input.current) { input.current.value = ""; input.current.click(); } }}>{status === "uploading" ? "Cargando archivo…" : isBook ? "Seleccionar libro de códigos" : "Seleccionar archivo"}</button>
    <input ref={input} className="sr-only" aria-label={isBook ? "Subir libro de códigos" : "Subir base de respuestas"} aria-describedby={limits} type="file" accept={isBook ? ".xlsx,.xls" : ".xlsx,.xls,.csv"} tabIndex={-1} disabled={busy} onChange={(event) => { const files = Array.from(event.target.files || []); event.target.value = ""; void select(files); }} />
    {filename && status !== "success" && <span className="upload-filename">{filename}</span>}
    {status === "uploading" && <><div role="progressbar" aria-label={`Carga de ${filename}`} className="upload-progress"><i /></div><p role="status">Cargando y validando el archivo…</p></>}
    {status === "success" && <p role="status" className="upload-success"><CheckCircle2 size={15} />Carga completada: {filename}</p>}
    {error && <p role="alert" className="field-error"><AlertCircle size={15} />{error}</p>}
  </div>;
}
