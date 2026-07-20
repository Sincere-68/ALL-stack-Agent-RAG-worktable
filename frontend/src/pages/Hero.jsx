import { useNavigate } from "react-router-dom";

const Hero = () => {
  const navigate = useNavigate();

  return (
    <main className="home-shell">
      <section className="hero">
        <div className="hero-content">
          <div className="hero-badge">LangGraph + RAG 工作台</div>

          <h1 className="hero-title">
            面向文档知识库的
            <span> Agentic AI 助手</span>
          </h1>

          <p className="hero-subtitle">
            上传论文、报告和表格文件，让智能体基于知识库检索、工具调用和会话记忆给出可追溯的回答。
          </p>

          <div className="hero-actions">
            <button className="btn primary" onClick={() => navigate("/chat")}>
              进入对话
            </button>
            <button className="btn secondary" onClick={() => navigate("/knowledge")}>
              管理知识库
            </button>
          </div>
        </div>

        <div className="hero-panel" aria-label="系统能力概览">
          <div className="panel-header">
            <span className="status-dot" />
            <span>Knowledge Agent Pipeline</span>
          </div>

          <div className="pipeline">
            <div className="pipeline-step">
              <strong>01</strong>
              <span>文档解析</span>
              <small>PDF / Word / Excel</small>
            </div>
            <div className="pipeline-step">
              <strong>02</strong>
              <span>语义检索</span>
              <small>Qwen/Qwen3-Embedding-8B</small>
            </div>
            <div className="pipeline-step">
              <strong>03</strong>
              <span>智能回答</span>
              <small>LLM + Tools</small>
            </div>
          </div>

          <div className="panel-metrics">
            <div>
              <span>RAG</span>
              <strong>Source aware</strong>
            </div>
            <div>
              <span>Agent</span>
              <strong>Tool enabled</strong>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
};

export default Hero;
