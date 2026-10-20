import * as Dialog from "@radix-ui/react-dialog";
import { X, FolderOpen } from "lucide-react";
import type { ReactNode } from "react";
import type { JobStatus } from "./types";

export const statusLabel: Record<JobStatus, string> = {
  PENDING: "Preparado",
  RUNNING: "En ejecución",
  PAUSED: "En pausa",
  FAILED: "Fallido",
  COMPLETED: "Completado",
};
export function Status({ status }: { status: JobStatus }) {
  return (
    <span className={`status status-${status.toLowerCase()}`}>
      <span />
      {statusLabel[status]}
    </span>
  );
}
export function Empty({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <FolderOpen size={28} strokeWidth={1.3} />
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="row between">
            <Dialog.Title>{title}</Dialog.Title>
            <Dialog.Close className="icon-button" aria-label="Cerrar diálogo">
              <X size={18} />
            </Dialog.Close>
          </div>
          <Dialog.Description>{description}</Dialog.Description>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export const number = (value: number) =>
  new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 }).format(value);
export const dollars = (value: number | null) =>
  value === null ? "No disponible" : `$${value.toFixed(5)}`;
export function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
