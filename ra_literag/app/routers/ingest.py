import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.config import OUTPUT_DIR, PARSE_METHOD, WORKSPACE_DEFAULT
from app.rag_cache import get_rag
from app.schemas import InsertContentRequest

router = APIRouter(tags=["ingest"])

@router.post("/content/insert", tags=["ingest"])
async def insert_content(req: InsertContentRequest):
    """Insert a pre-parsed content list (no file parsing) into the given workspace."""
    rag = await get_rag(req.workspace)
    await rag._ensure_lightrag_initialized()
    raw = [item.model_dump(exclude_none=True) for item in req.content_list]
    await rag.insert_content_list(
        content_list=raw,
        file_path=req.file_path,
        doc_id=req.doc_id,
        split_by_character=req.split_by_character,
        split_by_character_only=req.split_by_character_only,
    )
    return {"status": "ok", "file_path": req.file_path, "workspace": req.workspace}


@router.post("/documents/process", tags=["ingest"])
async def process_document(
    file: UploadFile = File(...),
    workspace: str = Form(default=WORKSPACE_DEFAULT, description="Tenant/workspace id"),
    output_dir: str | None = Form(None),
    parse_method: str | None = Form(None),
    parser: str | None = Form(None),
    doc_id: str | None = Form(None),
):
    """Upload a document and run full RAG processing (parse + index) for the given workspace."""
    rag = await get_rag(workspace)
    await rag._ensure_lightrag_initialized()
    output_dir = output_dir or OUTPUT_DIR
    parse_method = parse_method or PARSE_METHOD
    os.makedirs(output_dir, exist_ok=True)
    if parser:
        from raganything.parser import get_parser
        rag.update_config(parser=parser)
        rag.doc_parser = get_parser(parser)

    suffix = Path(file.filename or "doc").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        try:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Upload read failed: {e}")

    try:
        await rag.process_document_complete(
            file_path=tmp_path,
            output_dir=output_dir,
            parse_method=parse_method,
            doc_id=doc_id,
            file_name=file.filename,
        )
        return {"status": "ok", "filename": file.filename, "output_dir": output_dir, "workspace": workspace}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


