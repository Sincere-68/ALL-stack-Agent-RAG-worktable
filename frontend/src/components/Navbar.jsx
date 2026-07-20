import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();
  const isHome = location.pathname === "/";
  const isChat = location.pathname === "/chat";
  const isKnowledge = location.pathname === "/knowledge";

  const linkClass = (active) =>
    `px-3 py-1.5 rounded-lg text-sm transition ${
      active
        ? "bg-[#0F766E]/10 text-[#0F766E]"
        : "text-[#667085] hover:text-[#102A2A] hover:bg-[#F7FBFA]"
    }`;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-14 bg-white/90 backdrop-blur-md border-b border-[#DDE7E4]">
      <Link
        to="/"
        className="flex items-center gap-2 text-[#102A2A] font-semibold text-sm tracking-wide hover:opacity-80 transition"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-[#0F766E] text-white">
          AI
        </span>
        <span>Agent 工作台</span>
      </Link>

      <div className="flex items-center gap-1">
        <Link to="/" className={linkClass(isHome)}>
          首页
        </Link>
        <Link to="/chat" className={linkClass(isChat)}>
          工作台
        </Link>
        <Link to="/knowledge" className={linkClass(isKnowledge)}>
          知识库
        </Link>
      </div>
    </nav>
  );
}
