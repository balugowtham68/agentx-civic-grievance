import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import IntakePage from "./pages/IntakePage";
import ComplaintsPage from "./pages/ComplaintsPage";
import ComplaintDetailPage from "./pages/ComplaintDetailPage";
import ActivityPage, { SystemPage } from "./pages/PlaceholderPages";
import OfficialMailboxPage from "./pages/OfficialMailboxPage";
import Layout from "./components/Layout";
import { LanguageProvider } from "./context/LanguageContext";

function App() {
  return (
    <LanguageProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="intake" element={<IntakePage />} />
          <Route path="complaints" element={<ComplaintsPage />} />
          <Route path="complaints/:trackingId" element={<ComplaintDetailPage />} />
          <Route path="official-mailbox" element={<OfficialMailboxPage />} />
          <Route path="activity" element={<ActivityPage />} />
          <Route path="system" element={<SystemPage />} />
        </Route>
      </Routes>
    </LanguageProvider>
  );
}

export default App;