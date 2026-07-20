const TOOLS = [
  { id: "knowledge_search", label: "知识库检索", desc: "检索本地 RAG 知识库" },
  { id: "list_knowledge_documents", label: "文档列表", desc: "查看已索引文档" },
  { id: "calculator", label: "计算器", desc: "执行基础数学计算" },
  { id: "current_time", label: "当前时间", desc: "获取当前时间" },
];

export default function ToolPanel({ activeTool, onSelect }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {TOOLS.map((tool) => (
        <button
          key={tool.id}
          onClick={() => onSelect(activeTool === tool.id ? null : tool.id)}
          className={`flex items-center px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 ${
            activeTool === tool.id
              ? "bg-[#0F766E]/10 border-[#0F766E]/30 text-[#0F766E]"
              : "bg-white border-[#DDE7E4] text-[#667085] hover:text-[#102A2A] hover:bg-[#F7FBFA]"
          }`}
          title={tool.desc}
        >
          {tool.label}
        </button>
      ))}
    </div>
  );
}
