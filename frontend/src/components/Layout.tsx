import { Link, Outlet, useLocation } from "react-router-dom";
import { Shield, Activity, List, LayoutDashboard, Settings, Globe, Mail } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

export default function Layout() {
  const location = useLocation();
  const { t, selectedLang, setSelectedLang, activeLang } = useLanguage();

  const navItems = [
    { name: t.navHome || "Home", path: "/", icon: <LayoutDashboard size={18} /> },
    { name: t.navComplaints || "My Complaints", path: "/complaints", icon: <List size={18} /> },
    { name: "Official Mailbox", path: "/official-mailbox", icon: <Mail size={18} /> },
    { name: t.navActivity || "Activity", path: "/activity", icon: <Activity size={18} /> },
    { name: t.navSystem || "System", path: "/system", icon: <Settings size={18} /> },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-xl shadow-sm">
              S
            </div>
            <Link to="/" className="font-extrabold text-xl tracking-tight text-slate-900">
              {t.brand || "SPANDAN AI"}
            </Link>
          </div>

          <div className="flex items-center space-x-6">
            <nav className="hidden md:flex space-x-6">
              {navItems.map((item) => {
                const isActive =
                  location.pathname === item.path ||
                  (item.path !== "/" && location.pathname.startsWith(item.path));
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-1.5 text-sm font-semibold transition-colors ${
                      isActive ? "text-blue-600" : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {item.icon}
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Language Selector */}
            <div className="flex items-center space-x-2 bg-slate-100/80 hover:bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200/80 transition-colors">
              <Globe size={16} className="text-slate-500" />
              <select
                value={selectedLang}
                onChange={(e) => setSelectedLang(e.target.value)}
                aria-label="Select language"
                className="bg-transparent font-medium text-slate-700 text-sm outline-none cursor-pointer"
              >
                <option value="auto">Auto Detect ({activeLang.toUpperCase()})</option>
                <option value="en">English</option>
                <option value="te">తెలుగు (Telugu)</option>
                <option value="ta">தமிழ் (Tamil)</option>
                <option value="kn">ಕನ್ನಡ (Kannada)</option>
                <option value="hi">हिन्दी (Hindi)</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-grow flex flex-col w-full">
        <Outlet />
      </main>

      <footer className="bg-slate-900 py-8 text-slate-400 text-sm text-center">
        <div className="max-w-6xl mx-auto px-4 flex flex-col items-center">
          <div className="flex items-center space-x-2 mb-2 text-slate-200 font-semibold">
            <Shield size={18} className="text-blue-400" />
            <span>{t.trust || "Your language, your complaint, your tracking ID."}</span>
          </div>
          <p className="font-medium tracking-wide">
            {t.brand || "SPANDAN AI"} - {t.subtitle || "Autonomous Civic Grievance Redressal"}
          </p>
          <p className="mt-1 text-xs opacity-60">Hackathon Prototype</p>
        </div>
      </footer>
    </div>
  );
}
