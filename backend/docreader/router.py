"""
Explorion Document Reader – API Router
PDF upload, AI-powered explain (no RAG), and RAG-based Q&A.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List

import chromadb
import httpx
from groq import AsyncGroq
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_PREDICT_TOKENS = 300

CHUNK_SIZE_TOKENS = 200
CHUNK_OVERLAP_TOKENS = 40

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_store")
DOCUMENTS_JSON = os.path.join(UPLOAD_DIR, "documents.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class DocumentMeta(BaseModel):
    id: str
    title: str
    file_path: str
    uploaded_at: str


class ExplainRequest(BaseModel):
    document_id: str
    selected_text: str


class AskRequest(BaseModel):
    document_id: str
    question: str


# ---------------------------------------------------------------------------
# Persistent document registry
# ---------------------------------------------------------------------------

def _load_documents() -> Dict[str, DocumentMeta]:
    if not os.path.exists(DOCUMENTS_JSON):
        return {}
    try:
        with open(DOCUMENTS_JSON, "r", encoding="utf-8") as fh:
            raw: Dict[str, dict] = json.load(fh)
        return {k: DocumentMeta(**v) for k, v in raw.items()}
    except Exception:
        return {}


def _save_documents(docs: Dict[str, DocumentMeta]) -> None:
    with open(DOCUMENTS_JSON, "w", encoding="utf-8") as fh:
        json.dump({k: v.model_dump() for k, v in docs.items()}, fh, indent=2)


documents: Dict[str, DocumentMeta] = _load_documents()

# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("docreader")

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/docreader", tags=["Document Reader"])

# ---------------------------------------------------------------------------
# Helpers: embedding & LLM
# ---------------------------------------------------------------------------

EMBED_TIMEOUT = 60.0
LLM_TIMEOUT = 300.0


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Call Ollama /api/embed and return a list of embedding vectors."""
    if not texts:
        return []
    url = f"{OLLAMA_BASE_URL}/api/embed"
    t0 = time.time()
    logger.info(f"embed_texts: Sending request for {len(texts)} texts...")
    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT) as client:
        resp = await client.post(url, json={"model": EMBED_MODEL, "input": texts})
    logger.info(f"embed_texts: Got response in {time.time() - t0:.2f}s")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Embedding service error ({resp.status_code}): {resp.text}",
        )
    data = resp.json()
    embeddings = data.get("embeddings") or data.get("embedding")
    if embeddings is None:
        raise HTTPException(status_code=502, detail="Invalid embedding response from Ollama")
    if not embeddings:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned no vectors. Make sure the model is pulled: `ollama pull {EMBED_MODEL}`",
        )
    if isinstance(embeddings[0], (int, float)):
        return [embeddings]
    return embeddings


async def stream_completion(prompt: str) -> AsyncGenerator[str, None]:
    """Call Groq API with stream=True and yield SSE-formatted chunks."""
    yield ": heartbeat\n\n"

    approx_tokens = len(prompt) // 4
    logger.info(f"stream_completion: prompt length = {len(prompt)} chars (~{approx_tokens} tokens)")
    t_start = time.time()

    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        stream = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_PREDICT_TOKENS,
            stream=True,
        )

        first_token = True
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                if first_token:
                    logger.info(f"stream_completion: FIRST TOKEN at {time.time() - t_start:.2f}s")
                    first_token = False
                escaped = delta.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"

        logger.info(f"stream_completion: DONE in {time.time() - t_start:.2f}s")
        yield "data: [DONE]\n\n"

    except Exception as exc:
        logger.error(f"stream_completion: Groq error – {exc}")
        yield f"data: [ERROR] Groq API error: {exc}\n\n"
        yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def read_pdf_text(file_path: str) -> List[Dict]:
    reader = PdfReader(file_path)
    pages: List[Dict] = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page_number": idx + 1, "text": text})
    return pages


def chunk_pages(pages: List[Dict]) -> List[Dict]:
    tokens: List[str] = []
    page_token_bounds: List[Dict] = []
    cursor = 0
    for page in pages:
        page_tokens = page["text"].split()
        start = cursor
        tokens.extend(page_tokens)
        cursor += len(page_tokens)
        page_token_bounds.append(
            {"page_number": page["page_number"], "start": start, "end": cursor}
        )

    chunks: List[Dict] = []
    if not tokens:
        return chunks

    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        text = " ".join(chunk_tokens)

        page_number = 1
        for bounds in page_token_bounds:
            if bounds["start"] <= start < bounds["end"]:
                page_number = bounds["page_number"]
                break

        chunks.append(
            {
                "chunk_index": len(chunks),
                "page_number": page_number,
                "text": text,
            }
        )

        if end == len(tokens):
            break
        start = max(0, end - CHUNK_OVERLAP_TOKENS)

    return chunks


def get_or_create_collection(document_id: str):
    name = f"doc_{document_id}"
    try:
        return chroma_client.get_collection(name=name)
    except Exception:
        return chroma_client.create_collection(name=name)


def build_context_from_query(
    collection, query_embedding: List[float], document_id: str, n: int = 5
) -> str:
    try:
        count = collection.count()
    except Exception:
        count = n
    n_results = max(1, min(n, count))

    t0 = time.time()
    logger.info(f"build_context: Querying ChromaDB for doc={document_id} with n={n_results}...")
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"document_id": document_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vector search failed: {exc}") from exc

    logger.info(f"build_context: Query done in {time.time() - t0:.2f}s")

    metadatas = results.get("metadatas", [[]])[0]
    if not metadatas:
        raise HTTPException(status_code=404, detail="No context found for this document")

    chunks = [m.get("text", "") for m in metadatas if m.get("text")]
    return "\n\n---\n\n".join(chunks)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    """Health check for the document reader sub-system."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False
    return {"status": "ok", "ollama": ollama_ok, "groq_configured": bool(GROQ_API_KEY)}


@router.get("/documents")
async def list_documents():
    """Return metadata for all indexed documents."""
    return list(documents.values())


@router.get("/pdf/{document_id}")
async def serve_pdf(document_id: str):
    """Stream the original PDF file back to the client."""
    meta = documents.get(document_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(meta.file_path):
        raise HTTPException(status_code=404, detail="PDF file missing on server")
    return FileResponse(
        meta.file_path,
        media_type="application/pdf",
        filename=meta.title,
    )


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload, index, and store a PDF document."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        fname = file.filename or ""
        if not fname.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    document_id = str(uuid.uuid4())
    title = file.filename or f"document-{document_id}.pdf"
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.pdf")

    with open(file_path, "wb") as fh:
        fh.write(raw)

    # Extract text and chunk
    pages = read_pdf_text(file_path)
    chunks = chunk_pages(pages)

    if not chunks:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from this PDF",
        )

    # Embed in batches
    BATCH = 32
    all_embeddings: List[List[float]] = []
    for i in range(0, len(chunks), BATCH):
        batch_texts = [c["text"] for c in chunks[i : i + BATCH]]
        all_embeddings.extend(await embed_texts(batch_texts))

    # Store in ChromaDB
    collection = get_or_create_collection(document_id)
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "chunk_index": c["chunk_index"],
            "page_number": c["page_number"],
            "text": c["text"],
        }
        for c in chunks
    ]
    texts = [c["text"] for c in chunks]
    collection.add(ids=ids, embeddings=all_embeddings, metadatas=metadatas, documents=texts)

    # Persist document metadata
    meta = DocumentMeta(
        id=document_id,
        title=title,
        file_path=file_path,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
    )
    documents[document_id] = meta
    _save_documents(documents)

    return {"document_id": document_id, "title": title, "chunks": len(chunks)}


@router.post("/explain/stream")
async def explain_highlight_stream(body: ExplainRequest):
    """Streaming SSE explanation of highlighted text (no retrieval)."""
    if body.document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    if not body.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text must not be empty")

    prompt = (
        "You are a helpful assistant explaining a concept from a document.\n\n"
        f"Explain the following text briefly in 2-3 sentences:\n\n"
        f"\"{body.selected_text}\""
    )

    return StreamingResponse(
        stream_completion(prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ask/stream")
async def ask_question_stream(body: AskRequest):
    """Streaming SSE RAG-based answer."""
    logger.info(f"[POST /ask/stream] Received query: '{body.question}' for doc: {body.document_id}")
    t_total = time.time()

    if body.document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    collection = get_or_create_collection(body.document_id)
    [query_embedding] = await embed_texts([body.question])
    context = build_context_from_query(collection, query_embedding, body.document_id, n=3)

    prompt = (
        "You are answering questions about a PDF document.\n\n"
        "Use ONLY the information provided in the context below.\n"
        "Do not rely on external knowledge.\n\n"
        "Context:\n"
        f"{context}\n\n"
        "Question:\n"
        f"{body.question}\n\n"
        "Answer briefly using only the context."
    )

    logger.info(f"ask_stream prep total time before stream: {time.time() - t_total:.2f}s")

    return StreamingResponse(
        stream_completion(prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
