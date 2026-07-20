import { useState, useEffect, useRef } from "react";
import { uploadFile, getKnowledgeStats, deleteKnowledge, listDocuments } from "../utils/api";

export default function KnowledgeSection() {
  const [stats, setStats] = useState({ total_chunks: 0, embedding_model: "", embedding_collection: "" });
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [expandedDoc, setExpandedDoc] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [nextStats, nextDocs] = await Promise.all([getKnowledgeStats(), listDocuments()]);
      setStats(nextStats);
      setDocs(nextDocs);
    } catch {
      setStats({ total_chunks: 0, embedding_model: "", embedding_collection: "" });
      setDocs([]);
    }
  }

  async function handleFile(file) {
    setUploading(true);
    try {
      await uploadFile(file);
      await loadData();
    } catch (error) {
      alert(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(filename) {
    if (!confirm(`确认从知识库删除 "${filename}" 吗？`)) return;
    try {
      await deleteKnowledge(filename);
      await loadData();
    } catch (error) {
      alert(`Delete failed: ${error.message}`);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragOver(false);
    const file = event.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <main className="min-h-screen pt-14 bg-[#F7FBFA] text-[#102A2A]">
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
        <header className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold text-[#0F766E]">Knowledge Base</p>
            <h1 className="mt-2 text-3xl font-bold text-[#102A2A]">知识库</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#667085]">
              管理 RAG 检索资料。上传后的文档会被解析、分块并写入向量库，供 Agent 在工作台中引用。
            </p>
          </div>

          <button
            onClick={loadData}
            className="h-9 rounded-lg border border-[#DDE7E4] bg-white px-4 text-sm text-[#102A2A] hover:bg-[#F7FBFA]"
          >
            刷新
          </button>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-[#DDE7E4] bg-white p-5">
            <div className="text-sm text-[#667085]">文档数量</div>
            <div className="mt-2 text-2xl font-bold">{docs.length}</div>
          </div>
          <div className="rounded-xl border border-[#DDE7E4] bg-white p-5">
            <div className="text-sm text-[#667085]">检索块数量</div>
            <div className="mt-2 text-2xl font-bold">{stats.total_chunks}</div>
          </div>
          <div className="rounded-xl border border-[#DDE7E4] bg-white p-5">
            <div className="text-sm text-[#667085]">Embedding</div>
            <div className="mt-2 break-words text-base font-semibold">
              {stats.embedding_model || "Not configured"}
            </div>
            {stats.embedding_collection && (
              <div className="mt-1 break-words text-xs text-[#667085]">{stats.embedding_collection}</div>
            )}
          </div>
        </section>

        <section className="mt-4 rounded-xl border border-[#DDE7E4] bg-white p-5">
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${
              dragOver
                ? "border-[#0F766E] bg-[#0F766E]/8"
                : "border-[#DDE7E4] hover:border-[#0F766E]/40 hover:bg-[#F7FBFA]"
            }`}
          >
            {uploading ? (
              <div className="text-sm font-medium text-[#0F766E]">正在上传并解析...</div>
            ) : (
              <div className="text-sm text-[#667085]">
                拖拽文件到这里，或 <span className="font-medium text-[#0F766E]">点击选择文件</span>
                <div className="mt-2 text-xs text-[#98A2B3]">PDF / DOCX / TXT / MD / CSV / XLSX</div>
              </div>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md,.csv,.xlsx"
            onChange={(event) => event.target.files[0] && handleFile(event.target.files[0])}
            className="hidden"
          />
        </section>

        <section className="mt-4 rounded-xl border border-[#DDE7E4] bg-white">
          <div className="flex items-center justify-between border-b border-[#DDE7E4] px-5 py-4">
            <h2 className="text-sm font-semibold">文档列表</h2>
            <span className="text-xs text-[#667085]">{docs.length} documents</span>
          </div>

          {docs.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-[#667085]">暂无文档</div>
          ) : (
            <div className="divide-y divide-[#EEF2F0]">
              {docs.map((doc) => (
                <div key={doc.filename}>
                  <div
                    className="flex cursor-pointer items-center justify-between gap-4 px-5 py-4 hover:bg-[#F7FBFA]"
                    onClick={() => setExpandedDoc(expandedDoc === doc.filename ? null : doc.filename)}
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{doc.filename}</div>
                      <div className="mt-1 text-xs text-[#667085]">{doc.chunks.length} chunks</div>
                    </div>
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDelete(doc.filename);
                      }}
                      className="rounded-lg px-3 py-1.5 text-xs text-[#667085] hover:bg-red-50 hover:text-red-500"
                    >
                      删除
                    </button>
                  </div>

                  {expandedDoc === doc.filename && (
                    <div className="space-y-2 bg-[#F7FBFA] px-5 py-4">
                      {doc.chunks.map((chunk, index) => (
                        <div key={chunk.id} className="rounded-lg border border-[#DDE7E4] bg-white p-3">
                          <div className="mb-1 text-xs text-[#667085]">Chunk {index + 1}</div>
                          <div className="whitespace-pre-wrap text-xs leading-6 text-[#102A2A]">
                            {chunk.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
