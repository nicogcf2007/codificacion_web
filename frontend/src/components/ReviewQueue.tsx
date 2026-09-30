import React, { useEffect, useState } from 'react';
import { getJobReviewItems, handleAPIError, updateReviewItem } from '../services/api';
import type { ReviewItem } from '../types';
import { toast } from 'react-toastify';

interface ReviewQueueProps {
  jobId: string;
  onBack: () => void;
}

const ReviewQueue: React.FC<ReviewQueueProps> = ({ jobId, onBack }) => {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [filter, setFilter] = useState('REVIEW_REQUIRED');
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [reviewers, setReviewers] = useState<Record<string, string>>({});
  const [comments, setComments] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  const loadItems = async () => {
    setLoading(true);
    try {
      const loaded = await getJobReviewItems(jobId, filter || undefined);
      setItems(loaded);
      setCodes((current) => Object.fromEntries(loaded.map((item) => [item.id, current[item.id] ?? item.final_codes.join(';')])));
    } catch (error) {
      toast.error(`No se pudo cargar la revisión: ${handleAPIError(error)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadItems();
  }, [jobId, filter]);

  const saveItem = async (item: ReviewItem, status: string, suggested = false) => {
    setSavingId(item.id);
    try {
      const value = suggested ? item.suggested_codes.join(';') : (codes[item.id] || '');
      const finalCodes = value.split(';').map((code) => code.trim()).filter(Boolean);
      await updateReviewItem(item.id, {
        status,
        final_codes: finalCodes,
        reviewer: reviewers[item.id] || '',
        comment: comments[item.id] || '',
      });
      toast.success('Decisión guardada');
      await loadItems();
    } catch (error) {
      toast.error(`No se pudo guardar la decisión: ${handleAPIError(error)}`);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <p className="text-sm font-semibold text-amber-600 uppercase tracking-wide">Control humano</p>
            <h1 className="text-3xl font-bold text-slate-900">Bandeja de revisión</h1>
            <p className="text-slate-600 mt-1">Acepta, corrige o rechaza las sugerencias. Cada decisión queda auditada.</p>
          </div>
          <div className="flex gap-2">
            <select className="input-field w-auto" value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="REVIEW_REQUIRED">Pendientes</option>
              <option value="ACCEPTED">Aceptados</option>
              <option value="EDITED">Editados</option>
              <option value="REJECTED">Rechazados</option>
              <option value="">Todos</option>
            </select>
            <button onClick={onBack} className="btn-secondary">Volver</button>
          </div>
        </div>

        {loading ? <div className="card text-center py-12 text-slate-500">Cargando casos...</div> : items.length === 0 ? (
          <div className="card text-center py-12"><h2 className="text-xl font-bold text-slate-800">No hay casos en esta vista</h2><p className="text-slate-500 mt-2">La cola está vacía o todos los casos ya fueron resueltos.</p></div>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <article key={item.id} className="card border-l-4 border-amber-400">
                <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
                  <div><div className="text-xs text-slate-500">Fila {item.source_row} · {item.source_column}</div><h2 className="text-lg font-bold text-slate-800">{item.question}</h2></div>
                  <span className="px-2 py-1 text-xs rounded-full bg-amber-100 text-amber-800">{item.status}</span>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="rounded-lg bg-slate-50 border p-4"><p className="text-xs font-semibold text-slate-500 uppercase mb-2">Respuesta original</p><p className="text-slate-800 whitespace-pre-wrap">{item.response}</p><p className="text-xs text-slate-500 mt-4">{item.reason}</p></div>
                  <div className="space-y-3">
                    <div className="rounded-lg bg-blue-50 border border-blue-100 p-3"><p className="text-xs font-semibold text-blue-700 uppercase mb-1">Sugerencia automática</p><p className="font-mono text-blue-900">{item.suggested_codes.join('; ') || 'Sin código'}</p></div>
                    <label className="label">Códigos finales (separados por ;)<input className="input-field mt-1 font-mono" value={codes[item.id] || ''} onChange={(event) => setCodes((current) => ({ ...current, [item.id]: event.target.value }))} placeholder="01;05" /></label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3"><label className="label">Revisor<input className="input-field mt-1" value={reviewers[item.id] || ''} onChange={(event) => setReviewers((current) => ({ ...current, [item.id]: event.target.value }))} placeholder="Nombre o usuario" /></label><label className="label">Comentario<input className="input-field mt-1" value={comments[item.id] || ''} onChange={(event) => setComments((current) => ({ ...current, [item.id]: event.target.value }))} placeholder="Opcional" /></label></div>
                  </div>
                </div>
                <div className="flex flex-wrap justify-end gap-2 mt-5 pt-4 border-t">
                  <button disabled={savingId === item.id} onClick={() => void saveItem(item, 'ACCEPTED', true)} className="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50">Aceptar sugerencia</button>
                  <button disabled={savingId === item.id} onClick={() => void saveItem(item, 'EDITED')} className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">Guardar corrección</button>
                  <button disabled={savingId === item.id} onClick={() => void saveItem(item, 'REJECTED')} className="px-4 py-2 rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 disabled:opacity-50">Rechazar</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReviewQueue;
