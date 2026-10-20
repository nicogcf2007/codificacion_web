"""Single-worker durable execution with atomic prototype checkpoints."""
from __future__ import annotations
import asyncio
import os
import time
from sqlalchemy import select, update, insert, func
from fastapi import HTTPException
from . import db
from .repository import identity, now, record_activity
from .engine import ProviderPaused, parse_codes


class Runtime:
    def __init__(self, repo, provider):
        self.repo, self.provider = repo, provider
        self.tasks = {}

    def recover(self):
        with self.repo.engine.begin() as conn:
            ids = list(conn.scalars(select(db.jobs.c.id).where(db.jobs.c.status == 'RUNNING')))
            for id in ids:
                uncertain = conn.execute(update(db.prototypes).where(db.prototypes.c.job_id == id, db.prototypes.c.state == 'IN_FLIGHT').values(state='UNCERTAIN')).rowcount
                reason = 'Resultado incierto tras reinicio. Reintentar podría generar otro cargo.' if uncertain else 'Servidor reiniciado. Reanude desde el checkpoint.'
                conn.execute(update(db.jobs).where(db.jobs.c.id == id).values(status='PAUSED', pause_reason=reason, pause_requested=False, updated_at=now()))

    async def shutdown(self):
        for id in list(self.tasks):
            self.pause(id)
        if self.tasks:
            await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)

    async def start(self, id, retry_uncertain=False, actor_id=None):
        job = self.repo.get_job(id)
        if job['provider_mode'] != self.provider.mode:
            raise HTTPException(409, 'El proveedor debe coincidir con el modo guardado del trabajo')
        if self.provider.mode == 'blocked':
            raise HTTPException(503, 'Proveedor bloqueado. Configure CODING_PROVIDER y reinicie el servidor.')
        if self.provider.mode == 'openai' and not (getattr(self.provider, 'api_key', None) or getattr(self.provider, 'client', None)):
            raise HTTPException(503, 'Credencial del proveedor ausente en el servidor')
        with self.repo.engine.begin() as conn:
            uncertain = conn.scalar(select(func.count()).select_from(db.prototypes).where(db.prototypes.c.job_id == id, db.prototypes.c.state.in_(['IN_FLIGHT','UNCERTAIN'])))
            if uncertain and not retry_uncertain:
                raise HTTPException(409, 'Resultado incierto. Confirme explícitamente el riesgo de otro cargo antes de reintentar.')
            changed = conn.execute(update(db.jobs).where(db.jobs.c.id == id, db.jobs.c.status.in_(['PENDING','PAUSED'])).values(status='RUNNING', pause_requested=False, pause_reason=None, updated_at=now())).rowcount
            if not changed:
                raise HTTPException(409, 'Trabajo ya activo, completado o no reanudable')
            actor_id = actor_id or self.repo.execution_actor(id, conn)
            if actor_id:
                updated_actor = conn.execute(update(db.job_actors).where(db.job_actors.c.job_id == id).values(actor_id=actor_id)).rowcount
                if not updated_actor:
                    conn.execute(insert(db.job_actors).values(job_id=id, actor_id=actor_id))
            record_activity(conn, actor_id, 'job_resumed' if job['status'] == 'PAUSED' else 'job_started', 'job', id, job['project_id'], id)
            if uncertain:
                conn.execute(update(db.prototypes).where(db.prototypes.c.job_id == id, db.prototypes.c.state.in_(['IN_FLIGHT','UNCERTAIN'])).values(state='PENDING'))
                event_id = identity()
                conn.execute(insert(db.audit).values(id=event_id, job_id=id, record_id=None, action='uncertain_retry_authorized', payload={'prototypes':uncertain}, created_at=now()))
                if actor_id:
                    conn.execute(insert(db.audit_actors).values(event_id=event_id, actor_id=actor_id))
        self.tasks[id] = asyncio.create_task(self.run(id))
        return self.repo.get_job(id)

    def pause(self, id, actor_id=None):
        job = self.repo.require(db.jobs, id)
        with self.repo.engine.begin() as conn:
            changed = conn.execute(update(db.jobs).where(db.jobs.c.id == id, db.jobs.c.status == 'RUNNING').values(pause_requested=True, updated_at=now())).rowcount
            if not changed:
                raise HTTPException(409, 'Solo se puede pausar un trabajo en ejecución')
            record_activity(conn, actor_id or self.repo.execution_actor(id, conn), 'job_pause_requested', 'job', id, job['project_id'], id)
        return self.repo.get_job(id)

    def settle(self, id, status, reason=None):
        with self.repo.engine.begin() as conn:
            job = self.repo.require(db.jobs, id, conn)
            conn.execute(update(db.jobs).where(db.jobs.c.id == id).values(status=status, pause_reason=reason, pause_requested=False, updated_at=now()))
            record_activity(conn, self.repo.execution_actor(id, conn), 'job_completed' if status == 'COMPLETED' else 'job_paused', 'job', id, job['project_id'], id)

    def next_prototype(self, id):
        with self.repo.engine.begin() as conn:
            row = conn.execute(select(db.prototypes).where(db.prototypes.c.job_id == id, db.prototypes.c.state == 'PENDING').order_by(db.prototypes.c.ordinal).limit(1)).mappings().first()
            if row is None:
                return None
            item = dict(row)
            changed = conn.execute(update(db.prototypes).where(db.prototypes.c.id == item['id'], db.prototypes.c.state == 'PENDING').values(state='IN_FLIGHT', attempts=db.prototypes.c.attempts + 1)).rowcount
            if not changed:
                raise RuntimeError('Prototype claim failed')
            job = self.repo.require(db.jobs, id, conn)
            metrics = {**job['metrics'], 'api_calls':job['metrics']['api_calls'] + 1}
            conn.execute(update(db.jobs).where(db.jobs.c.id == id).values(metrics=metrics, updated_at=now()))
            return item

    def checkpoint(self, id, prototype, result, seconds):
        with self.repo.engine.begin() as conn:
            job = self.repo.require(db.jobs, id, conn)
            question = next(question for question in job['questions'] if question['id'] == prototype['question_id'])
            codes, invalid = parse_codes(result.raw, question['categories'], question['max_labels'])
            values=[]
            for index, member in enumerate(prototype['members']):
                fuzzy = member['text'].strip() != prototype['text']
                reason = 'Salida inválida del modelo' if invalid else 'Código 77: nueva categoría / otro' if '77' in codes else 'Agrupamiento difuso: confirmar intención' if fuzzy else None
                values.append(dict(id=identity(), job_id=id, question_id=question['id'], response_id=member['response_id'], column_name=question['column_name'], text_original=member['text'], codes=codes, confidence=None, was_grouped=index > 0 or fuzzy, prototype_id=prototype['id'], review_status='PENDING' if reason else 'APPROVED', review_reason=reason))
            conn.execute(insert(db.records),values)
            conn.execute(update(db.prototypes).where(db.prototypes.c.id == prototype['id']).values(state='COMPLETED', result={'codes':codes, 'input_tokens':result.input_tokens, 'output_tokens':result.output_tokens}))
            processed = job['processed_records'] + len(values)
            active = job['active_seconds'] + seconds
            metrics = {**job['metrics']}
            metrics['input_tokens'] += result.input_tokens
            metrics['output_tokens'] += result.output_tokens
            metrics['records_per_second'] = processed / active if active else 0
            metrics['eta_seconds'] = (job['total_records'] - processed) / metrics['records_per_second'] if metrics['records_per_second'] else None
            if self.provider.mode == 'demo':
                metrics['cost_usd'] = metrics['saved_usd'] = 0.0
            else:
                input_rate, output_rate = os.getenv('INPUT_USD_PER_MILLION'), os.getenv('OUTPUT_USD_PER_MILLION')
                if input_rate and output_rate:
                    metrics['cost_usd'] = (metrics['input_tokens'] * float(input_rate) + metrics['output_tokens'] * float(output_rate)) / 1000000
                    baseline = os.getenv('BASELINE_RECORD_USD')
                    if baseline:
                        metrics['saved_usd'] = max(0, job['total_records'] * float(baseline) - metrics['cost_usd'])
            conn.execute(update(db.jobs).where(db.jobs.c.id == id).values(processed_records=processed, metrics=metrics, active_seconds=active, updated_at=now()))
            record_activity(conn, self.repo.execution_actor(id, conn), 'job_checkpoint', 'job', id, job['project_id'], id)

    async def run(self, id):
        current = None
        try:
            while True:
                job = self.repo.require(db.jobs, id)
                if job['pause_requested']:
                    self.settle(id,'PAUSED','Pausa solicitada. Resultados en curso guardados.')
                    return
                current = self.next_prototype(id)
                if current is None:
                    self.settle(id,'COMPLETED')
                    return
                question = next(question for question in job['questions'] if question['id'] == current['question_id'])
                started = time.monotonic()
                result = await asyncio.to_thread(self.provider.code, question['question_text'], current['text'], question['categories'], question['max_labels'])
                self.checkpoint(id,current,result,time.monotonic()-started)
                current = None
                await asyncio.sleep(0)
        except BaseException as error:
            safe = isinstance(error, ProviderPaused) and not error.uncertain
            if current:
                with self.repo.engine.begin() as conn:
                    conn.execute(update(db.prototypes).where(db.prototypes.c.id == current['id']).values(state='PENDING' if safe else 'UNCERTAIN'))
            reason = error.reason if isinstance(error, ProviderPaused) else 'Resultado incierto por interrupción. Reintentar podría generar otro cargo.'
            self.settle(id, 'PAUSED', reason)
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
        finally:
            self.tasks.pop(id, None)
