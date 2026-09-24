from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core import build, Problem
from app.memory_review import review


class Turn(BaseModel):
    request_id: UUID
    text: str = Field(min_length=1, max_length=2000)
    without_recall: bool = False
    provider: str | None = Field(default=None, max_length=32)
    model: str | None = Field(default=None, max_length=128)


class Reset(BaseModel):
    generation: str
    confirmation: str


class Review(BaseModel):
    version: str
    source_id: str = ''
    category: str = 'about_me'
    people: list[str] = Field(default_factory=list, max_length=20)
    accept: bool


class MemoryChange(BaseModel):
    revision: int
    text: str | None = Field(default=None, max_length=4000)
    delete: bool = False


class PrivateMessage(BaseModel):
    role: str = Field(pattern='^(USER|ASSISTANT)$')
    text: str = Field(min_length=1, max_length=16000)


class PrivateTurn(BaseModel):
    history: list[PrivateMessage] = Field(min_length=1, max_length=101)
    provider: str = Field(max_length=32)
    model: str = Field(max_length=128)


class CacheExample(BaseModel):
    enabled: bool = False
    provider: str = Field(max_length=32)
    model: str = Field(max_length=128)
    variant: int = Field(default=0, ge=0, le=1)


class DocumentPreview(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=200000)


class DocumentSelection(BaseModel):
    passage_id: str
    text: str = Field(min_length=1, max_length=4000)
    category: str


class DocumentApproval(DocumentPreview):
    content_hash: str
    generation: str
    selections: list[DocumentSelection] = Field(min_length=1, max_length=300)


def create_app(service=None):
    service = service or build()
    api = FastAPI(title='Shared Context Demo', docs_url=None, redoc_url=None, openapi_url=None)
    api.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', 'testserver'])

    @api.middleware('http')
    async def local_requests(request: Request, call_next):
        if request.method != 'GET':
            origin = request.headers.get('origin')
            if (request.headers.get('x-demo-request') != '1' or
                (origin and origin != f'{request.url.scheme}://{request.url.netloc}')):
                return JSONResponse({'code': 'invalid_origin', 'detail': 'Use the local application.'}, status_code=403)
        try:
            response = await call_next(request)
        except Exception:
            return JSONResponse({'code': 'storage_unavailable', 'detail':
                'A service or storage operation failed. Reload to check saved state before retrying.'}, status_code=503)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @api.exception_handler(Problem)
    async def problem(_request, exc):
        return JSONResponse({'code': exc.code, 'detail': exc.message}, status_code=exc.status)

    @api.get('/api/state')
    def state():
        return service.snapshot()

    @api.post('/api/conversations')
    def conversation():
        return service.new_conversation()

    @api.post('/api/documents/preview')
    def preview_document(body: DocumentPreview):
        from app.documents import preview
        return preview(**body.model_dump())

    @api.post('/api/documents/approve')
    def approve_document(body: DocumentApproval):
        from app.documents import approve
        return approve(service, **body.model_dump())

    @api.post('/api/private/turns')
    def private_turn(body: PrivateTurn):
        return service.private_answer([m.model_dump() for m in body.history], body.provider, body.model)

    @api.post('/api/examples/cache')
    def cache_example(body: CacheExample):
        from app.cache_example import run
        return run(service, **body.model_dump())

    @api.post('/api/candidates/{candidate_id}/review')
    def review_candidate(candidate_id: str, body: Review):
        if any(len(p) > 100 for p in body.people):
            raise Problem('invalid_people', 'Person labels must be at most 100 characters.', 422)
        return review(service, candidate_id, **body.model_dump())

    @api.get('/api/export')
    def export():
        return JSONResponse(service.export(), headers={
            'Content-Disposition': 'attachment; filename="shared-context-export.json"'})

    @api.post('/api/memories/{memory_id}')
    def change_memory(memory_id: str, body: MemoryChange):
        from app.memory_lifecycle import change
        return change(service, memory_id, **body.model_dump())

    @api.post('/api/conversations/{cid}/turns')
    def turn(cid: str, body: Turn):
        if not body.text.strip():
            raise Problem('empty_message', 'Enter a message.', 422)
        return service.send(cid, str(body.request_id), body.text.strip(), body.without_recall, body.provider, body.model)

    @api.post('/api/jobs/{job_id}/retry')
    def retry(job_id: str):
        service.retry_job(job_id)
        return {'queued': True}

    @api.post('/api/reset')
    def reset(body: Reset):
        if body.confirmation != 'RESET':
            raise Problem('confirmation_required', 'Type RESET to clear this demo.', 422)
        return service.reset(body.generation)

    dist = Path(__file__).resolve().parents[1] / 'frontend/dist'
    if dist.exists():
        api.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return api


app = create_app()
