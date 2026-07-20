import { Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import Hero from "./pages/Hero.jsx";
import ChatSection from "./pages/ChatSection.jsx";
import KnowledgeSection from "./pages/KnowledgeSection.jsx";

const App = () => {
  return (
    <>
      <Navbar />

      <Routes>
        <Route path="/" element={<Hero />} />
        <Route path="/chat" element={<ChatSection />} />
        <Route path="/knowledge" element={<KnowledgeSection />} />
      </Routes>
    </>
  );
};

export default App;
