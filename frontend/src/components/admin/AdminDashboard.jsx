import { useState, useEffect } from "react";

export default function AdminDashboard({ onLogout }) {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [metrics, setMetrics] = useState(null);
  const [customersList, setCustomersList] = useState([]);
  const [applicationsList, setApplicationsList] = useState([]);
  const [collectionsList, setCollectionsList] = useState([]);
  const [auditLogsList, setAuditLogsList] = useState([]);

  useEffect(() => {
    fetch("/api/v1/admin/metrics").then(res => res.json()).then(setMetrics).catch(console.error);
    fetch("/api/v1/admin/customers").then(res => res.json()).then(setCustomersList).catch(console.error);
    fetch("/api/v1/admin/applications").then(res => res.json()).then(setApplicationsList).catch(console.error);
    fetch("/api/v1/admin/collections").then(res => res.json()).then(setCollectionsList).catch(console.error);
    fetch("/api/v1/admin/audit-logs").then(res => res.json()).then(setAuditLogsList).catch(console.error);
  }, []);

  const adminModules = [
    { id: "dashboard", label: "📊 Overview" },
    { id: "customers", label: "👥 Customers & KYC" },
    { id: "applications", label: "📝 Applications" },
    { id: "loans", label: "💸 Active Loans" },
    { id: "payments", label: "💳 Payments & Ledger" },
    { id: "collections", label: "🚨 Collections & Arrears" },
    { id: "products", label: "⚙️ Loan Products" },
    { id: "compliance", label: "🛡️ Compliance & Audit" },
    { id: "reports", label: "📈 Portfolio Reports" },
    { id: "settings", label: "🔧 System Settings" },
  ];

  return (
    <div className="min-h-screen bg-ledger-paper font-sans text-ledger-ink flex flex-col md:flex-row">
      {/* Admin Sidebar Navigation */}
      <aside className="w-full md:w-64 bg-kina-deep text-ledger-paper flex flex-col border-b md:border-b-0 md:border-r border-ledger-rule shadow-sm">
        <div className="p-6 border-b border-ledger-rule/20 text-center md:text-left">
          <h2 className="font-display text-xl font-bold uppercase tracking-wider text-kina-gold">
            Sparkle Consultants
          </h2>
          <p className="text-[10px] text-ledger-paper/60 uppercase tracking-widest mt-0.5">
            Admin Console
          </p>
        </div>

        <nav className="flex-1 p-4 space-y-1 font-display text-xs uppercase tracking-wider font-semibold">
          {adminModules.map((mod) => (
            <button
              key={mod.id}
              onClick={() => setActiveModule(mod.id)}
              className={`w-full flex items-center px-4 py-2.5 rounded transition-all ${
                activeModule === mod.id
                  ? "bg-kina-gold text-kina-deep font-bold shadow-sm"
                  : "text-ledger-paper/85 hover:bg-white/10"
              }`}
            >
              {mod.label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-ledger-rule/20">
          <button
            onClick={onLogout}
            className="w-full py-2 text-xs font-display uppercase tracking-wider font-semibold text-risk-high hover:bg-risk-high/10 rounded border border-risk-high/30"
          >
            🚪 Sign Out
          </button>
        </div>
      </aside>

      {/* Main Admin Surface */}
      <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto w-full space-y-6">
        <header className="border-b border-ledger-rule pb-4 flex justify-between items-center">
          <div>
            <span className="text-xs uppercase tracking-widest text-bilum-teal font-medium">Sparkle Consultants Administration</span>
            <h1 className="font-display text-3xl font-bold text-kina-deep uppercase">{adminModules.find(m => m.id === activeModule)?.label}</h1>
          </div>
          <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-3 py-1 rounded">System Online</span>
        </header>

        {/* 1. Dashboard Module */}
        {activeModule === "dashboard" && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Total Customers</span>
                <p className="text-2xl font-bold text-kina-deep mt-1">{metrics?.total_customers || 0}</p>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Capital Out</span>
                <p className="text-2xl font-bold text-kina-deep mt-1">PGK {(metrics?.total_capital_out || 0).toLocaleString()}</p>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Pending Applications</span>
                <p className="text-2xl font-bold text-kina-gold mt-1">{metrics?.pending_applications || 0}</p>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Overdue Collections</span>
                <p className="text-2xl font-bold text-red-600 mt-1">{metrics?.overdue_collections || 0}</p>
              </div>
            </div>
          </div>
        )}

        {/* 2. Customers Module */}
        {activeModule === "customers" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">Customer Directory & Risk Profiles</h3>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-ledger-rule font-display uppercase text-ledger-ink/60">
                  <th className="py-2">Full Name</th>
                  <th>Public Servant</th>
                  <th>Status</th>
                  <th>Risk Flag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ledger-rule/20">
                {customersList.map((c) => (
                  <tr key={c.id}>
                    <td className="py-2.5 font-bold">{c.full_name}</td>
                    <td>{c.is_public_servant ? "Yes (Alesco)" : "No"}</td>
                    <td><span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">{c.status}</span></td>
                    <td><span className={`px-2 py-0.5 rounded ${c.risk_flag === 'high' ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>{c.risk_flag}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 3. Applications Module */}
        {activeModule === "applications" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">Submitted Loan Applications</h3>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-ledger-rule font-display uppercase text-ledger-ink/60">
                  <th className="py-2">App ID</th>
                  <th>Amount Requested</th>
                  <th>Term</th>
                  <th>Purpose</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ledger-rule/20">
                {applicationsList.map((a) => (
                  <tr key={a.id}>
                    <td className="py-2.5 font-mono">{a.id.slice(0, 8)}</td>
                    <td>PGK {a.amount_requested.toLocaleString()}</td>
                    <td>{a.term_requested} fortnights</td>
                    <td>{a.purpose}</td>
                    <td><span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded font-semibold">{a.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 4. Collections Module */}
        {activeModule === "collections" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">Collections Workflow (10 Stages)</h3>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-ledger-rule font-display uppercase text-ledger-ink/60">
                  <th className="py-2">Loan ID</th>
                  <th>Collection Stage</th>
                  <th>Days Overdue</th>
                  <th>Amount Overdue</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ledger-rule/20">
                {collectionsList.map((col) => (
                  <tr key={col.id}>
                    <td className="py-2.5 font-mono">{col.loan_id.slice(0, 8)}</td>
                    <td><span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded font-semibold">{col.stage}</span></td>
                    <td>{col.days_overdue} days</td>
                    <td>PGK {col.amount_overdue.toLocaleString()}</td>
                    <td>{col.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 5. Compliance & Audit Module */}
        {activeModule === "compliance" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">Immutable Audit Trail</h3>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-ledger-rule font-display uppercase text-ledger-ink/60">
                    <th className="py-2">Timestamp</th>
                    <th>Action</th>
                    <th>Entity Type</th>
                    <th>Entity ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ledger-rule/20 font-mono">
                  {auditLogsList.map((log) => (
                    <tr key={log.id}>
                      <td className="py-2">{new Date(log.timestamp).toLocaleString()}</td>
                      <td className="font-bold text-kina-deep">{log.action}</td>
                      <td>{log.entity_type}</td>
                      <td>{log.entity_id?.slice(0, 8) || "N/A"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Other Modules Placeholders */}
        {["loans", "payments", "products", "reports", "settings"].includes(activeModule) && (
          <div className="bg-white p-8 border border-ledger-rule rounded shadow-sm text-xs space-y-2">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">{activeModule.toUpperCase()} Control Module</h3>
            <p className="text-ledger-ink/70">Full administrative management active for Sparkle Consultants platform operator.</p>
          </div>
        )}
      </main>
    </div>
  );
}
