import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  sendMessage,
  listConversations,
  deleteConversation,
  getConversationMessages,
  listDocuments,
  getKnowledgeFileUrl,
} from "../utils/api";
import ToolPanel from "./ToolPanel";

export default function Chat() {
  const navigate = useNavigate();

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const sendingRef = useRef(false);

  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const activeConvIdRef = useRef(null);

  const [documents, setDocuments] = useState([]);
  const [selectedPdf, setSelectedPdf] = useState("");
  const [activeTool, setActiveTool] = useState(null);

  const pdfDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().endsWith(".pdf"),
  );
  const latestSources =
    [...messages].reverse().find((message) => message.role === "assistant" && message.sources?.length)
      ?.sources || [];

  useEffect(() => {
    loadConversations();
    loadDocuments();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    activeConvIdRef.current = activeConvId;
  }, [activeConvId]);

  async function loadConversations() {
    try {
      const data = await listConversations();
      setConversations(data);
    } catch {
      setConversations([]);
    }
  }

  async function loadDocuments() {
    try {
      const data = await listDocuments();
      setDocuments(data);
      const firstPdf = data.find((doc) => doc.filename.toLowerCase().endsWith(".pdf"));
      setSelectedPdf((current) => current || firstPdf?.filename || "");
    } catch {
      setDocuments([]);
      setSelectedPdf("");
    }
  }

  function handleNewChat() {
    setMessages([]);
    setActiveConvId(null);
    setActiveTool(null);
  }

  async function handleSelectChat(convId) {
    setActiveConvId(convId);
    try {
      const msgs = await getConversationMessages(convId);
      setMessages(msgs.map((m) => ({ role: m.role, content: m.content })));
    } catch {
      setMessages([]);
    }
  }

  async function handleDeleteChat(convId, event) {
    event.stopPropagation();
    try {
      await deleteConversation(convId);
      if (activeConvId === convId) {
        setMessages([]);
        setActiveConvId(null);
      }
      loadConversations();
    } catch {
      loadConversations();
    }
  }

  async function handleSend() {
    if (!input.trim() || sendingRef.current) return;

    sendingRef.current = true;
    const requestConvId = activeConvId;
    const userMsg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const data = await sendMessage(userMsg, requestConvId, activeTool);
      const stillViewingSameChat =
        activeConvIdRef.current === requestConvId ||
        (!requestConvId && activeConvIdRef.current === null);

      if (stillViewingSameChat) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.response, sources: data.sources || [] },
        ]);
      }

      if (!requestConvId && data.conversation_id && stillViewingSameChat) {
        setActiveConvId(data.conversation_id);
        loadConversations();
      }
    } catch {
      const stillViewingSameChat =
        activeConvIdRef.current === requestConvId ||
        (!requestConvId && activeConvIdRef.current === null);
      if (!stillViewingSameChat) return;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "请求失败，请检查后端服务或稍后重试。" },
      ]);
    } finally {
      setLoading(false);
      sendingRef.current = false;
      setActiveTool(null);
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex bg-[#F7FBFA] text-[#102A2A]" style={{ top: "56px" }}>
      <aside className="hidden w-1/2 max-w-[56rem] shrink-0 flex-col border-r border-[#DDE7E4] bg-white lg:flex">
        <div className="flex items-center justify-between border-b border-[#DDE7E4] px-4 py-3">
          <div>
            <div className="text-sm font-semibold">原文 PDF</div>
            <div className="text-xs text-[#667085]">对照原文进行知识库问答</div>
          </div>
          <button
            onClick={() => navigate("/knowledge")}
            className="rounded-lg border border-[#DDE7E4] px-3 py-1.5 text-xs text-[#667085] hover:bg-[#F7FBFA] hover:text-[#0F766E]"
          >
            知识库
          </button>
        </div>

        <div className="border-b border-[#DDE7E4] p-3">
          {pdfDocuments.length > 0 ? (
            <select
              value={selectedPdf}
              onChange={(event) => setSelectedPdf(event.target.value)}
              className="h-9 w-full rounded-lg border border-[#DDE7E4] bg-white px-3 text-sm text-[#102A2A] outline-none focus:border-[#0F766E]"
            >
              {pdfDocuments.map((doc) => (
                <option key={doc.filename} value={doc.filename}>
                  {doc.filename}
                </option>
              ))}
            </select>
          ) : (
            <div className="rounded-lg border border-dashed border-[#DDE7E4] bg-[#F7FBFA] px-3 py-3 text-sm text-[#667085]">
              暂无 PDF。请先到知识库上传 PDF 文件。
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 bg-[#F7FBFA]">
          {selectedPdf ? (
            <iframe
              title={selectedPdf}
              src={`${getKnowledgeFileUrl(selectedPdf)}#zoom=page-width`}
              className="h-full w-full border-0"
            />
          ) : (
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-[#667085]">
              选择一个 PDF 后，这里会显示原始文档。
            </div>
          )}
        </div>
      </aside>

      <div className="flex w-52 shrink-0 flex-col border-r border-[#DDE7E4] bg-white max-lg:hidden xl:w-56">
        <div className="flex flex-col gap-2 border-b border-[#DDE7E4] p-3">
          <button
            onClick={handleNewChat}
            className="w-full rounded-lg bg-[#0F766E] px-3 py-2 text-sm font-medium text-white transition hover:bg-[#0B625C]"
          >
            新建对话
          </button>
          <button
            onClick={loadDocuments}
            className="w-full rounded-lg border border-[#DDE7E4] bg-[#F7FBFA] px-3 py-2 text-sm text-[#102A2A] transition hover:bg-[#EEF7F4]"
          >
            刷新文档
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-[#667085]">暂无历史会话</div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => handleSelectChat(conv.id)}
                className={`group flex cursor-pointer items-center justify-between border-b border-[#EEF2F0] px-4 py-3 text-sm transition ${
                  activeConvId === conv.id
                    ? "bg-[#0F766E]/8 text-[#0F766E]"
                    : "text-[#667085] hover:bg-[#F7FBFA] hover:text-[#102A2A]"
                }`}
              >
                <span className="flex-1 truncate">{conv.title}</span>
                <button
                  onClick={(event) => handleDeleteChat(conv.id, event)}
                  className="ml-2 text-[#667085] opacity-0 transition hover:text-red-500 group-hover:opacity-100"
                  aria-label="删除会话"
                >
                  删除
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col bg-[#F7FBFA]">
        <header className="flex h-14 items-center justify-between border-b border-[#DDE7E4] bg-white px-6 text-sm font-medium">
          <span>知识库智能问答</span>
          <button
            onClick={() => navigate("/")}
            className="text-[#667085] transition hover:text-[#0F766E]"
          >
            返回首页
          </button>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center text-sm text-[#667085]">
              <div className="mb-3 text-base font-semibold text-[#102A2A]">开始一次知识库问答</div>
              <p className="max-w-md leading-7">
                左侧查看原始 PDF，中间与 Agent 对话。你可以询问文档结论、数据来源、章节内容，也可以选择工具辅助检索或计算。
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[88%] rounded-xl border px-4 py-3 text-sm leading-relaxed ${
                  message.role === "user"
                    ? "border-[#0F766E] bg-[#0F766E] text-white"
                    : "border-[#DDE7E4] bg-white text-[#102A2A]"
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                {message.role === "assistant" && message.sources?.length > 0 && (
                  <div className="mt-3 border-t border-[#DDE7E4] pt-3">
                    <div className="mb-2 text-xs font-semibold text-[#0F766E]">引用来源</div>
                    <div className="space-y-2">
                      {message.sources.map((source) => (
                        <div
                          key={`${source.rank}-${source.source}-${source.page}-${source.chunk_type}`}
                          className="rounded-lg border border-[#EEF2F0] bg-[#F7FBFA] px-3 py-2 text-xs text-[#667085]"
                        >
                          <div className="flex items-center justify-between gap-2 text-[#102A2A]">
                            <span className="truncate font-medium">{source.source}</span>
                            <span className="shrink-0 text-[#0F766E]">
                              {source.page ? `P.${source.page}` : "Page ?"}
                            </span>
                          </div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            <span>{source.chunk_type}</span>
                            {source.table_number && <span>Table {source.table_number}</span>}
                            {source.section_path && <span className="truncate">{source.section_path}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="animate-pulse rounded-xl border border-[#DDE7E4] bg-white px-4 py-2 text-sm text-[#667085]">
                Agent 正在分析...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <footer className="space-y-3 border-t border-[#DDE7E4] bg-white p-4">
          <ToolPanel activeTool={activeTool} onSelect={setActiveTool} />

          <div className="flex items-center gap-3 rounded-xl border border-[#DDE7E4] bg-white px-4 py-3 shadow-sm">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && !loading && handleSend()}
              placeholder="输入问题，例如：这篇 PDF 的核心方法是什么？"
              disabled={loading}
              className="flex-1 bg-transparent text-sm text-[#102A2A] outline-none placeholder:text-[#98A2B3] disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="rounded-lg bg-[#0F766E] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#0B625C] disabled:opacity-40"
            >
              发送
            </button>
          </div>
        </footer>
      </div>

      <aside className="hidden w-72 flex-col border-l border-[#DDE7E4] bg-white 2xl:flex">
        <div className="border-b border-[#DDE7E4] px-5 py-4">
          <div className="text-sm font-semibold text-[#102A2A]">运行上下文</div>
          <div className="mt-1 text-xs text-[#667085]">工具、步骤和引用来源</div>
        </div>

        <div className="space-y-4 overflow-y-auto p-4">
          <section className="rounded-xl border border-[#DDE7E4] bg-[#F7FBFA] p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">当前工具</h3>
              <span className="rounded-md bg-[#0F766E]/10 px-2 py-1 text-xs text-[#0F766E]">
                {activeTool || "Auto"}
              </span>
            </div>
            <p className="text-xs leading-5 text-[#667085]">
              用户选择工具后，这里显示工具说明、参数状态和调用结果摘要。未选择时由 Agent 自动判断。
            </p>
          </section>

          <section className="rounded-xl border border-[#DDE7E4] bg-white p-4">
            <div className="mb-3 text-sm font-semibold">已可用工具</div>
            <div className="space-y-2">
              {[
                ["知识库检索", "本地"],
                ["文档列表", "本地"],
                ["计算器", "本地"],
                ["当前时间", "本地"],
              ].map(([name, status]) => (
                <div key={name} className="flex items-center justify-between rounded-lg border border-[#EEF2F0] px-3 py-2">
                  <span className="text-sm text-[#102A2A]">{name}</span>
                  <span className="text-xs text-[#0F766E]">{status}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-[#DDE7E4] bg-white p-4">
            <div className="mb-3 text-sm font-semibold">MCP 接入建议</div>
            <div className="space-y-2">
              {[
                ["文件系统", "本地文件读写"],
                ["SQLite / Postgres", "数据库查询"],
                ["Git 仓库", "代码检索"],
                ["浏览器", "可选联网"],
              ].map(([name, desc]) => (
                <div key={name} className="rounded-lg border border-[#EEF2F0] px-3 py-2">
                  <div className="text-sm text-[#102A2A]">{name}</div>
                  <div className="mt-1 text-xs text-[#98A2B3]">{desc}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-[#DDE7E4] bg-white p-4">
            <div className="mb-3 text-sm font-semibold">执行步骤</div>
            <ol className="space-y-3 text-xs text-[#667085]">
              <li className="flex gap-2">
                <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-[#0F766E]/10 text-center leading-5 text-[#0F766E]">1</span>
                <span>理解用户问题并判断是否需要工具或知识库。</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-[#0F766E]/10 text-center leading-5 text-[#0F766E]">2</span>
                <span>优先使用本地工具；必要时再接入 MCP 或在线工具。</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-[#0F766E]/10 text-center leading-5 text-[#0F766E]">3</span>
                <span>汇总证据、生成回答并记录会话。</span>
              </li>
            </ol>
          </section>

          <section className="rounded-xl border border-[#DDE7E4] bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold">引用来源</div>
              <span className="text-xs text-[#98A2B3]">{latestSources.length}</span>
            </div>
            {latestSources.length > 0 ? (
              <div className="space-y-2">
                {latestSources.map((source) => (
                  <div key={`${source.rank}-${source.source}-${source.page}`} className="rounded-lg border border-[#EEF2F0] px-3 py-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-[#102A2A]">{source.source}</div>
                        <div className="mt-1 truncate text-xs text-[#667085]">
                          {source.section_path || source.caption || source.content_type}
                        </div>
                      </div>
                      <span className="shrink-0 rounded-md bg-[#0F766E]/10 px-2 py-1 text-xs text-[#0F766E]">
                        {source.page ? `P.${source.page}` : "N/A"}
                      </span>
                    </div>
                    <p className="mt-2 line-clamp-3 text-xs leading-5 text-[#667085]">{source.preview}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs leading-5 text-[#667085]">
                发送知识库问题后，这里会显示命中的文档、页码、章节和片段摘要。
              </p>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}
