import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from backend.schemas import KnowledgeUploadResponse, KnowledgeStats
from agent.knowledge.document_parser import parse_document
from agent.knowledge.semantic_splitter import semantic_split
from agent.knowledge.vectorstore import add_documents, get_stats, delete_by_source, list_documents
from agent.logger.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx"}


@router.post("/upload", response_model=KnowledgeUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    # 检查文件格式
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 保存文件
    file_path = UPLOAD_DIR / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    try:
        # 加载 → 切分 → 存入向量库
        elements = parse_document(str(file_path))
        chunks, metadatas = semantic_split(elements)
        add_documents(chunks, metadatas=metadatas)

        return {
            "filename": file.filename,
            "chunks": len(chunks),
            "message": f"Successfully indexed {len(chunks)} chunks from {file.filename}",
        }
    except Exception as e:
        # 加载失败则删除文件
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=KnowledgeStats)
def knowledge_stats():
    return get_stats()


@router.get("/list")
def knowledge_list():
    return list_documents()


@router.get("/file/{filename:path}")
def get_knowledge_file(filename: str):
    file_path = (UPLOAD_DIR / filename).resolve()
    upload_root = UPLOAD_DIR.resolve()

    if upload_root not in file_path.parents and file_path != upload_root:
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    if file_path.suffix.lower() == ".pdf":
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=file_path.name,
            content_disposition_type="inline",
        )
    return FileResponse(path=file_path, media_type="application/octet-stream")


@router.delete("/{filename}")
def delete_knowledge(filename: str):
    # 删除向量库中的记录
    delete_by_source(filename)
    # 删除上传的文件
    file_path = UPLOAD_DIR / filename
    file_path.unlink(missing_ok=True)
    return {"message": f"Deleted {filename}"}
