"""v1 resource routes: validation stays at the boundary."""
import asyncio
import json
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from modern.schemas import CodebookCreate, JobCreate, ResumeRequest, ReviewUpdate, BatchReview
from modern.study import MAX_BYTES
from modern import results


def build_router(repo, authorize, mode, runtime):
    router = APIRouter(prefix="/api/v1", dependencies=[Depends(authorize)])

    @router.get("/projects/{project_id}/codebooks")
    def list_books(project_id: str):
        return {"codebooks": repo.list_books(project_id)}

    @router.post("/projects/{project_id}/codebooks/preview")
    async def preview_books(project_id: str, file: UploadFile = File(...), context=Depends(authorize)):
        try:
            content = await file.read(MAX_BYTES + 1)
            return repo.preview_books(project_id, file.filename or "", content)
        finally:
            await file.close()

    @router.post("/projects/{project_id}/codebooks", status_code=201)
    def create_book(project_id: str, data: CodebookCreate, context=Depends(authorize)):
        return repo.create_book(project_id, data, context['user']['id'])

    @router.post("/projects/{project_id}/codebooks/import", status_code=201)
    async def import_books(project_id: str, file: UploadFile = File(...), survey_id: str = Form(...),
                           selections: str = Form(...), context=Depends(authorize)):
        try:
            try:
                specs = json.loads(selections)
            except (ValueError, TypeError):
                raise ValueError('Selecciones JSON inválidas') from None
            content = await file.read(MAX_BYTES + 1)
            return repo.import_books(project_id, survey_id, file.filename or "", content, specs, context['user']['id'])
        finally:
            await file.close()

    @router.get("/projects/{project_id}/surveys")
    def surveys(project_id: str):
        return {"surveys": repo.list_surveys(project_id)}

    @router.post("/projects/{project_id}/surveys", status_code=201)
    async def upload(project_id: str, file: UploadFile = File(...), context=Depends(authorize)):
        try:
            content = await file.read(MAX_BYTES + 1)
            return repo.upload(project_id, file.filename or "", content, context['user']['id'])
        finally:
            await file.close()

    @router.post("/coding/jobs", status_code=201)
    def create_job(data: JobCreate, context=Depends(authorize)):
        return repo.create_job(data, mode, context['user']['id'])

    @router.get("/jobs")
    def jobs(project_id: str | None = None):
        return {"jobs": repo.list_jobs(project_id)}

    @router.get("/jobs/{job_id}")
    def job(job_id: str):
        return repo.get_job(job_id)

    @router.post("/jobs/{job_id}/start")
    @router.post("/jobs/{job_id}/resume")
    async def start(job_id: str, data: ResumeRequest = ResumeRequest(), context=Depends(authorize)):
        return await runtime.start(job_id, data.retry_uncertain, context['user']['id'])

    @router.post("/jobs/{job_id}/pause")
    def pause(job_id: str, context=Depends(authorize)):
        return runtime.pause(job_id, context['user']['id'])

    @router.get("/jobs/{job_id}/records")
    def records(job_id: str, review_only: bool = False, limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
        return {"records": repo.list_records(job_id, review_only, limit, offset)}

    @router.patch("/jobs/{job_id}/records/{record_id}")
    def approve(job_id: str, record_id: str, data: ReviewUpdate, context=Depends(authorize)):
        return repo.audited_review(context['user']['id'], job_id, results.approve, record_id, data.codes)

    @router.post("/jobs/{job_id}/review/batch")
    def review_batch(job_id: str, data: BatchReview, context=Depends(authorize)):
        return repo.audited_review(context['user']['id'], job_id, results.batch, data)

    @router.get("/jobs/{job_id}/analytics")
    def analytics(job_id: str):
        return results.analytics(repo, job_id)

    @router.get("/jobs/{job_id}/export")
    def export(job_id: str, format: Literal['csv','xlsx'] = 'xlsx'):
        content, content_type = results.export(repo, job_id, format)
        return Response(content, media_type=content_type, headers={'Content-Disposition': f'attachment; filename="CNC-{job_id}.{format}"'})

    @router.get("/jobs/{job_id}/events")
    async def events(job_id: str, request: Request):
        repo.get_job(job_id)

        async def stream():
            while not await request.is_disconnected():
                # A long-lived connection is not an authorization lease.
                try:
                    await asyncio.to_thread(authorize, request)
                except HTTPException:
                    break
                job = repo.get_job(job_id)
                payload = {'job':job, 'records':repo.list_activity(job_id)}
                yield 'event: snapshot\ndata: ' + json.dumps(payload,ensure_ascii=False) + '\n\n'
                if job['status'] != 'RUNNING':
                    break
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

    return router
