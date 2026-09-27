import { useEffect, useState } from "react";
import { Mail, CheckCircle, XCircle, AlertTriangle, Shield, RefreshCw, ExternalLink, Inbox } from "lucide-react";

interface MailboxItem {
  id: string;
  complaint_id: string;
  tracking_id: string;
  event_type: string;
  recipient: string;
  title: string;
  message: string;
  created_at: string;
  current_status: string;
  urls: {
    accept?: string;
    reject?: string;
    higher_accept?: string;
    status?: string;
  };
  delivered: boolean;
  issue?: string;
  location?: string;
  category?: string;
}

export default function OfficialMailboxPage() {
  const [items, setItems] = useState<MailboxItem[]>([]);
  const [activeTab, setActiveTab] = useState<"authority" | "higher">("authority");
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchMailbox = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/review/mailbox");
      if (res.ok) {
        const data = await res.json();
        setItems(data);
      }
    } catch (err) {
      console.error("Failed to load mailbox", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMailbox();
    const interval = setInterval(fetchMailbox, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (url: string, label: string) => {
    try {
      setActionMessage(`Processing ${label}...`);
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`✓ Action Successful! New Status: ${data.status}`);
        fetchMailbox();
      } else {
        setActionMessage(`Action error: ${res.statusText}`);
      }
    } catch (err: any) {
      setActionMessage(`Error: ${err.message}`);
    }
  };

  const authorityItems = items.filter(
    (i) => i.event_type === "AUTHORITY_REVIEW_EMAIL" || i.recipient.includes("impardhu")
  );

  const higherItems = items.filter(
    (i) => i.event_type === "HIGHER_OFFICIAL_ESCALATION_EMAIL" || i.recipient.includes("guttula")
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-200 gap-4">
        <div>
          <div className="flex items-center space-x-2.5 mb-1.5">
            <div className="p-2 rounded-xl bg-blue-100 text-blue-700">
              <Mail size={24} />
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">
              Official Grievance Review Mailbox
            </h1>
          </div>
          <p className="text-sm text-slate-600">
            Dedicated administrative review console for Local Authority & Higher Officials
          </p>
        </div>

        <button
          onClick={fetchMailbox}
          disabled={loading}
          className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-colors shadow-sm self-start md:self-auto"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span>Refresh Mailbox</span>
        </button>
      </div>

      {/* Gmail SMTP Notice Banner */}
      <div className="my-6 p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 shadow-xs">
        <div className="flex items-start space-x-3">
          <div className="p-2 rounded-xl bg-amber-200 text-amber-900 shrink-0 mt-0.5">
            <AlertTriangle size={18} />
          </div>
          <div className="text-xs space-y-1">
            <div className="font-bold text-amber-950 text-sm">
              Gmail SMTP Security Status
            </div>
            <p className="text-amber-800 leading-relaxed">
              Google blocks automated scripts from using normal login passwords (<code className="font-mono bg-amber-100 px-1 py-0.5 rounded">mine3127</code> / <code className="font-mono bg-amber-100 px-1 py-0.5 rounded">GOWTHAM@143</code>).
              Google requires a <strong>16-character App Password</strong> from{" "}
              <a
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noreferrer"
                className="underline font-bold text-amber-950 hover:text-blue-700"
              >
                myaccount.google.com/apppasswords
              </a>{" "}
              for direct delivery to your phone's Gmail app.
            </p>
            <p className="text-amber-800 font-medium">
              ✨ <strong>Demo Advantage:</strong> All emails, official layouts, and one-click Accept/Reject buttons are live in this mailbox!
            </p>
          </div>
        </div>
      </div>

      {/* Action Feedback Banner */}
      {actionMessage && (
        <div className="mb-6 p-3.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-sm font-semibold flex items-center justify-between animate-in fade-in duration-200">
          <span>{actionMessage}</span>
          <button
            onClick={() => setActionMessage(null)}
            className="text-emerald-700 hover:text-emerald-950 font-black text-xs ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 mb-6">
        <button
          onClick={() => setActiveTab("authority")}
          className={`flex items-center space-x-2 px-5 py-3 border-b-2 font-bold text-sm transition-colors ${
            activeTab === "authority"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Inbox size={16} />
          <span>Local Authority Inbox</span>
          <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-mono bg-blue-100 text-blue-800">
            {authorityItems.length}
          </span>
          <span className="text-xs text-slate-400 font-normal">
            (impardhu3127@gmail.com)
          </span>
        </button>

        <button
          onClick={() => setActiveTab("higher")}
          className={`flex items-center space-x-2 px-5 py-3 border-b-2 font-bold text-sm transition-colors ${
            activeTab === "higher"
              ? "border-rose-600 text-rose-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Shield size={16} />
          <span>Higher Official Escalations</span>
          <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-mono bg-rose-100 text-rose-800">
            {higherItems.length}
          </span>
          <span className="text-xs text-slate-400 font-normal">
            (guttulagowthamgandhi@gmail.com)
          </span>
        </button>
      </div>

      {/* Email List */}
      <div className="space-y-4">
        {(activeTab === "authority" ? authorityItems : higherItems).length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-200 p-8">
            <Inbox size={40} className="text-slate-300 mx-auto mb-3" />
            <h3 className="font-bold text-slate-700 text-base">No Emails in this Mailbox Yet</h3>
            <p className="text-slate-500 text-xs mt-1 max-w-sm mx-auto">
              Submit a civic grievance on the Home page to dispatch a live review email.
            </p>
          </div>
        ) : (
          (activeTab === "authority" ? authorityItems : higherItems).map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-all"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                <div className="flex items-center space-x-2.5">
                  <span className="font-mono text-xs font-black px-2.5 py-1 bg-slate-900 text-white rounded-lg">
                    {item.tracking_id}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">
                    To: <strong className="text-slate-800">{item.recipient}</strong>
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-xs">
                  <span className="text-slate-400">
                    {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full font-bold text-xs ${
                      item.current_status === "ACCEPTED_BY_AUTHORITY"
                        ? "bg-emerald-100 text-emerald-800"
                        : item.current_status === "ESCALATED"
                        ? "bg-rose-100 text-rose-800"
                        : item.current_status === "ACCEPTED_BY_HIGHER_AUTHORITY"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-slate-100 text-slate-800"
                    }`}
                  >
                    Status: {item.current_status}
                  </span>
                </div>
              </div>

              <div className="py-3">
                <h3 className="font-black text-slate-900 text-base mb-1.5">{item.title}</h3>
                <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                  {item.message}
                </p>
                {item.location && (
                  <p className="text-xs text-slate-500 mt-2">
                    📍 <strong>Location:</strong> {item.location} &bull; <strong>Category:</strong> {item.category || "General"}
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center space-x-2">
                  {activeTab === "authority" && (
                    <>
                      <button
                        onClick={() => item.urls.accept && handleAction(item.urls.accept, "Accept by Authority")}
                        className="inline-flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-colors shadow-xs"
                      >
                        <CheckCircle size={14} />
                        <span>✓ Accept Complaint</span>
                      </button>

                      <button
                        onClick={() => item.urls.reject && handleAction(item.urls.reject, "Reject & Escalate")}
                        className="inline-flex items-center space-x-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-colors shadow-xs"
                      >
                        <XCircle size={14} />
                        <span>✗ Reject & Escalate</span>
                      </button>
                    </>
                  )}

                  {activeTab === "higher" && (
                    <button
                      onClick={() => item.urls.higher_accept && handleAction(item.urls.higher_accept, "Accept by Higher Official")}
                      className="inline-flex items-center space-x-1.5 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-colors shadow-xs"
                    >
                      <Shield size={14} />
                      <span>✓ Accept Escalated Grievance</span>
                    </button>
                  )}
                </div>

                <a
                  href={`http://localhost:8000/api/v1/review/${item.tracking_id}/status`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center space-x-1 text-xs font-bold text-slate-500 hover:text-slate-800"
                >
                  <span>Review Portal URL</span>
                  <ExternalLink size={12} />
                </a>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
