from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import Response

from .. import config, ingest, store

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

router = APIRouter(prefix="/api/manuals", tags=["manuals"])


@router.get("")
def list_manuals():
    return store.list_manuals()


@router.post("", status_code=202)
async def upload_manual(
    background_tasks: BackgroundTasks, file: UploadFile, title: str | None = None
):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    body = await file.read()
    if len(body) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            413, f"File too large. Max size is {config.MAX_UPLOAD_BYTES // (1024*1024)} MB."
        )
    if not body.startswith(b"%PDF-"):
        raise HTTPException(400, "File does not look like a valid PDF.")

    manual_title = title or (file.filename or "manual").rsplit(".", 1)[0]
    entry = store.create_manual_entry(
        title=manual_title,
        filename=file.filename or "manual.pdf",
        chunk_chars=config.DEFAULT_CHUNK_CHARS,
        chunk_overlap_chars=config.DEFAULT_CHUNK_OVERLAP_CHARS,
    )
    manual_id = entry["id"]

    # Stored filename is derived from our own generated manual_id, never from the
    # client-supplied filename, so it cannot be used for path traversal.
    dest = config.UPLOADS_DIR / f"{manual_id}.pdf"
    dest.write_bytes(body)

    background_tasks.add_task(ingest.ingest_manual, manual_id, dest)

    return store.get_manual(manual_id)


@router.delete("/{manual_id}")
def delete_manual(manual_id: str):
    entry = store.get_manual(manual_id)
    if not entry:
        raise HTTPException(404, "Manual not found.")
    store.delete_manual(manual_id)
    pdf_path = config.UPLOADS_DIR / f"{manual_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    return {"deleted": True}


@router.get("/{manual_id}/pages/{page_number}")
def get_page_image(manual_id: str, page_number: int):
    entry = store.get_manual(manual_id)
    if not entry:
        raise HTTPException(404, "Manual not found.")
    if page_number < 1 or page_number > entry.get("num_pages", 0):
        raise HTTPException(404, "Page out of range.")

    pdf_path = config.UPLOADS_DIR / f"{manual_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(404, "Manual PDF not found on disk.")

    doc = fitz.open(pdf_path)
    try:
        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=120)
        png_bytes = pix.tobytes("png")
    finally:
        doc.close()

    return Response(content=png_bytes, media_type="image/png")
