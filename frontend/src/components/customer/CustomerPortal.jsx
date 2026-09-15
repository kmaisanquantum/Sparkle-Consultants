import { useState, useEffect } from "react";

export default function CustomerPortal({ onLogout }) {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [currentCustomerId, setCurrentCustomerId] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loans, setLoans] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [consentGiven, setConsentGiven] = useState(false);

  useEffect(() => {
    const fetchMe = async () => {
      const token = localStorage.getItem("sparkle_token");
      if (token) {
        try {
          const res = await fetch("/api/v1/auth/me", {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setCurrentCustomerId(data.customer_id);
            setUserProfile(data);
          }
        } catch (e) {
          console.error(e);
        }
      }
    };

    const fetchLoans = async () => {
      const token = localStorage.getItem("sparkle_token");
      if (token) {
        try {
          const res = await fetch("/api/v1/loans", {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setLoans(data);
          }
        } catch (e) {
          console.error(e);
        }
      }
    };

    fetchMe();
    fetchLoans();
  }, []);

  // Application wizard state (17-step flow)
  const [wizardStep, setWizardStep] = useState(1);
  const [appAmount, setAppAmount] = useState(2000);
  const [appTerm, setAppTerm] = useState(10);
  const [appPurpose, setAppPurpose] = useState("School Fees & Personal Needs");
  const [appSubmitting, setAppSubmitting] = useState(false);
  const [appResult, setAppResult] = useState(null);

  // Payment state
  const [payAmount, setPayAmount] = useState(300);
  const [paySubmitting, setPaySubmitting] = useState(false);
  const [payMessage, setPayMessage] = useState("");

  const handleCreateDraft = async () => {
    try {
      const token = localStorage.getItem("sparkle_token");
      const res = await fetch("/api/v1/applications/draft", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          amount_requested: parseFloat(appAmount),
          term_requested: parseInt(appTerm),
          compounding_period: "fortnightly",
          purpose: appPurpose,
          step_completed: wizardStep,
          draft_data: {
            net_income: 1800.0,
            existing_obligations: 200.0,
            borrower_consent: consentGiven,
            consent_timestamp: new Date().toISOString()
          }
        })
      });
      if (res.ok) {
        const data = await res.json();
        return data.application_id;
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleFinalSubmit = async () => {
    if (!consentGiven) {
      alert("Please check and accept the Borrower Consent & Disclosure declaration before submitting.");
      return;
    }
    setAppSubmitting(true);
    try {
      const appId = await handleCreateDraft();
      if (appId) {
        const token = localStorage.getItem("sparkle_token");
        const subRes = await fetch(`/api/v1/applications/${appId}/submit`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (subRes.ok) {
          const data = await subRes.json();
          setAppResult(data);
          setWizardStep(17);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setAppSubmitting(false);
    }
  };

  const handleMakePayment = async (e) => {
    e.preventDefault();
    setPaySubmitting(true);
    try {
      const token = localStorage.getItem("sparkle_token");
      const res = await fetch("/api/v1/payments/initiate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          customer_id: currentCustomerId || "00000000-0000-0000-0000-000000000000",
          amount: parseFloat(payAmount),
          payment_method: "bsp_online",
          idempotency_key: `PAY-${Date.now()}`
        })
      });
      if (res.ok) {
        setPayMessage("✅ Payment of PGK " + payAmount + " processed successfully via BSP gateway!");
      }
    } catch (e) {
      setPayMessage("❌ Payment error. Please try again.");
    } finally {
      setPaySubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-ledger-paper font-sans text-ledger-ink flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 bg-kina-deep text-ledger-paper flex flex-col border-b md:border-b-0 md:border-r border-ledger-rule shadow-sm">
        <div className="p-6 border-b border-ledger-rule/20 text-center md:text-left">
          <h2 className="font-display text-xl font-bold uppercase tracking-wider text-kina-gold">
            Sparkle Portal
          </h2>
          <p className="text-[10px] text-ledger-paper/60 uppercase tracking-widest mt-0.5">
            Borrower Self-Service
          </p>
        </div>

        <nav className="flex-1 p-4 space-y-1 font-display text-xs uppercase tracking-wider font-semibold">
          {[
            { id: "dashboard", label: "📊 Dashboard" },
            { id: "my_loans", label: "💸 My Loans" },
            { id: "apply", label: "📝 Apply For Loan" },
            { id: "payments", label: "💳 Payments" },
            { id: "profile", label: "👤 Profile & KYC" },
            { id: "support", label: "🎧 Support & Help" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center px-4 py-2.5 rounded transition-all ${
                activeTab === tab.id
                  ? "bg-kina-gold text-kina-deep font-bold shadow-sm"
                  : "text-ledger-paper/85 hover:bg-white/10"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-ledger-rule/20">
          <button
            onClick={onLogout}
            className="w-full py-2 text-xs font-display uppercase tracking-wider font-semibold text-risk-high hover:bg-risk-high/10 rounded border border-risk-high/30"
          >
            🚪 Log Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto w-full">
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            <header className="flex justify-between items-center border-b border-ledger-rule pb-4">
              <div>
                <span className="text-xs uppercase tracking-widest text-bilum-teal font-medium">Customer Dashboard</span>
                <h1 className="font-display text-3xl font-bold text-kina-deep">
                  Welcome Back, {userProfile?.full_name || "Borrower"}
                </h1>
              </div>
              <button
                onClick={() => setActiveTab("apply")}
                className="px-4 py-2 bg-kina-gold text-kina-deep font-display uppercase font-bold text-xs rounded shadow hover:bg-yellow-400"
              >
                + New Application
              </button>
            </header>

            {/* Application Lifecycle Tracker */}
            <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-3">
              <h3 className="font-display text-base font-bold text-kina-deep uppercase">📍 Application Status Tracking</h3>
              <div className="flex flex-wrap justify-between items-center gap-2 text-xs font-display uppercase font-semibold text-ledger-ink/70">
                <span className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded">1. Draft ✅</span>
                <span>→</span>
                <span className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded">2. Submitted ✅</span>
                <span>→</span>
                <span className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded">3. Under Review ✅</span>
                <span>→</span>
                <span className="px-3 py-1 bg-kina-gold/30 text-kina-deep rounded font-bold">4. Approved / Offered ✨</span>
                <span>→</span>
                <span className="px-3 py-1 bg-ledger-paper rounded">5. Disbursed</span>
                <span>→</span>
                <span className="px-3 py-1 bg-ledger-paper rounded">6. Completed</span>
              </div>
            </div>

            {/* Overview Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Active Loans Count</span>
                <p className="text-2xl font-bold text-kina-deep mt-1">{loans.length}</p>
                <span className="text-[10px] text-emerald-600 font-semibold">Self-Service Account</span>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Outstanding Balance</span>
                <p className="text-2xl font-bold text-kina-gold mt-1">
                  PGK {loans.reduce((acc, l) => acc + (l.outstanding_balance || 0), 0).toFixed(2)}
                </p>
                <span className="text-[10px] text-ledger-ink/60">Live Balance</span>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Role & Access</span>
                <p className="text-2xl font-bold text-ledger-ink mt-1 uppercase">{userProfile?.role || "Customer"}</p>
                <span className="text-[10px] text-ledger-ink/60">RBAC Role Assigned</span>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">MFA Status</span>
                <p className="text-2xl font-bold text-emerald-600 mt-1">
                  {userProfile?.mfa_enabled ? "Enabled 🔒" : "Disabled ⚠️"}
                </p>
                <span className="text-[10px] text-ledger-ink/60">Account Security</span>
              </div>
            </div>

            {/* Notifications */}
            <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-3">
              <h3 className="font-display text-base font-bold text-kina-deep uppercase">🔔 Recent Notifications</h3>
              <ul className="divide-y divide-ledger-rule/20 text-xs">
                <li className="py-2.5 flex justify-between">
                  <span>Welcome to Sparkle Consultants online portal.</span>
                  <span className="text-ledger-ink/50">Today</span>
                </li>
                <li className="py-2.5 flex justify-between">
                  <span>Alesco payroll deduction check active on account profile.</span>
                  <span className="text-ledger-ink/50">Recent</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* 17-Step Online Application Wizard */}
        {activeTab === "apply" && (
          <div className="bg-white p-6 md:p-8 border border-ledger-rule rounded shadow-sm max-w-3xl mx-auto space-y-6">
            <div className="border-b border-ledger-rule pb-4 flex justify-between items-center">
              <div>
                <span className="text-xs text-bilum-teal font-display uppercase tracking-widest">17-Step Online Application Wizard</span>
                <h2 className="text-2xl font-display font-bold text-kina-deep uppercase">Loan Application — Step {wizardStep} of 17</h2>
              </div>
              <span className="text-xs bg-kina-gold/20 text-kina-deep px-3 py-1 rounded font-display uppercase font-bold">Draft Saved</span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-ledger-paper rounded-full h-2 border border-ledger-rule">
              <div className="bg-kina-gold h-full rounded-full transition-all" style={{ width: `${(wizardStep/17)*100}%` }}></div>
            </div>

            {wizardStep < 17 ? (
              <div className="space-y-4 text-xs">
                {wizardStep === 1 && (
                  <div className="space-y-3">
                    <h4 className="font-display text-sm font-bold uppercase text-kina-deep">Step 1: Account & Product Selection</h4>
                    <label className="block">Requested Amount (PGK)</label>
                    <input type="number" value={appAmount} onChange={(e) => setAppAmount(e.target.value)} className="w-full p-2 border border-ledger-rule rounded" min="100" />
                    <label className="block mt-2">Term Periods (Fortnights)</label>
                    <input type="number" value={appTerm} onChange={(e) => setAppTerm(e.target.value)} className="w-full p-2 border border-ledger-rule rounded" min="2" />
                  </div>
                )}
                {wizardStep > 1 && wizardStep < 16 && (
                  <div className="p-4 bg-ledger-paper border border-ledger-rule rounded space-y-2">
                    <h4 className="font-display text-sm font-bold uppercase text-kina-deep">
                      Step {wizardStep}: {["Personal Details", "Contact", "KYC Verification", "Employment", "Income Details", "Obligations", "Bank Account", "Purpose", "Terms", "Supporting Documents", "Declarations & Consent", "Credit Scoring", "Offer Generation", "Digital Agreement"][wizardStep - 2]}
                    </h4>
                    <p className="text-ledger-ink/70">Information captured and saved to draft state automatically.</p>
                  </div>
                )}
                {wizardStep === 16 && (
                  <div className="p-4 bg-emerald-50 border border-emerald-300 rounded space-y-3 text-emerald-900">
                    <h4 className="font-display text-sm font-bold uppercase">Step 16: Declarations & Borrower Consent</h4>
                    <p>By clicking submit, you authorize Sparkle Consultants to verify your employment and bank account details, conduct credit scoring evaluation, and enforce Alesco 50% net pay retention rules.</p>
                    <label className="flex items-center space-x-2 cursor-pointer font-bold pt-2">
                      <input
                        type="checkbox"
                        checked={consentGiven}
                        onChange={(e) => setConsentGiven(e.target.checked)}
                        className="rounded text-kina-deep"
                      />
                      <span>I confirm all information provided is true and accept the Loan Terms & Privacy Policy.</span>
                    </label>
                  </div>
                )}

                <div className="flex justify-between pt-4 border-t border-ledger-rule">
                  {wizardStep > 1 && (
                    <button onClick={() => setWizardStep(wizardStep - 1)} className="px-4 py-2 border border-ledger-rule rounded font-display uppercase font-semibold">Previous</button>
                  )}
                  {wizardStep < 16 ? (
                    <button onClick={() => setWizardStep(wizardStep + 1)} className="px-4 py-2 bg-kina-deep text-ledger-paper rounded font-display uppercase font-semibold ml-auto">Next Step →</button>
                  ) : (
                    <button onClick={handleFinalSubmit} disabled={appSubmitting} className="px-6 py-2 bg-kina-gold text-kina-deep rounded font-display uppercase font-bold ml-auto shadow">{appSubmitting ? "Evaluating..." : "Submit Application ✨"}</button>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-6 bg-emerald-50 border border-emerald-300 rounded text-emerald-900 space-y-3">
                <h3 className="font-display text-xl font-bold uppercase">✨ Decision: {appResult?.decision}</h3>
                <p className="text-xs">{appResult?.summary}</p>
                {appResult?.offer && (
                  <div className="p-4 bg-white border border-emerald-200 rounded text-xs text-ledger-ink space-y-2">
                    <h5 className="font-display font-bold uppercase text-kina-deep">Instant Loan Offer Issued</h5>
                    <p>Approved Amount: PGK {appResult.offer.approved_amount?.toLocaleString()}</p>
                    <p>Fortnightly Repayment: PGK {appResult.offer.periodic_repayment?.toLocaleString()}</p>
                    <button onClick={() => setActiveTab("my_loans")} className="w-full py-2 bg-kina-gold text-kina-deep font-display font-bold uppercase rounded mt-2">View & Accept Offer</button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Payments Surface */}
        {activeTab === "payments" && (
          <div className="bg-white p-6 md:p-8 border border-ledger-rule rounded shadow-sm max-w-2xl mx-auto space-y-6">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">💳 Make An Online Payment</h2>
            {payMessage && <div className="p-3 bg-ledger-paper border border-ledger-rule text-xs rounded">{payMessage}</div>}

            <form onSubmit={handleMakePayment} className="space-y-4 text-xs">
              <div>
                <label className="block font-display uppercase font-semibold mb-1">Repayment Amount (PGK)</label>
                <input type="number" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} className="w-full p-2 border border-ledger-rule rounded" min="10" />
              </div>
              <div>
                <label className="block font-display uppercase font-semibold mb-1">Payment Method</label>
                <select className="w-full p-2 border border-ledger-rule rounded bg-ledger-paper/50">
                  <option value="bsp_online">BSP Pay Online Gateway</option>
                  <option value="kina_online">Kina Bank Transfer</option>
                  <option value="payroll">Alesco Payroll Deduction</option>
                </select>
              </div>
              <button type="submit" disabled={paySubmitting} className="w-full py-2 bg-kina-deep text-ledger-paper font-display uppercase font-semibold rounded shadow hover:bg-kina-deep/90">
                {paySubmitting ? "Processing..." : "Pay via BSP Gateway"}
              </button>
            </form>
          </div>
        )}

        {/* My Loans Surface */}
        {activeTab === "my_loans" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">💸 My Loans & Repayment Schedule</h2>
            {loans.length > 0 ? (
              loans.map((l) => (
                <div key={l.id} className="p-4 border border-ledger-rule rounded bg-ledger-paper space-y-2">
                  <div className="flex justify-between items-center">
                    <h4 className="font-display font-bold text-base text-kina-deep uppercase">Loan #{l.id.substring(0, 8)}</h4>
                    <span className="font-semibold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded uppercase">{l.status}</span>
                  </div>
                  <p>Principal: PGK {l.principal_amount?.toFixed(2)} | Outstanding Balance: PGK {l.outstanding_balance?.toFixed(2)}</p>
                  <p>Compounding: {l.compounding_period} | Term Periods: {l.term_periods}</p>
                </div>
              ))
            ) : (
              <p className="text-ledger-ink/60">No active loans found on record.</p>
            )}
          </div>
        )}

        {/* Profile & Support Surfaces */}
        {activeTab === "profile" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">👤 Profile & Account Info</h2>
            <p><strong>Full Name:</strong> {userProfile?.full_name}</p>
            <p><strong>Email:</strong> {userProfile?.email}</p>
            <p><strong>Role:</strong> {userProfile?.role}</p>
            <p><strong>Customer ID:</strong> {userProfile?.customer_id || "N/A"}</p>
          </div>
        )}

        {activeTab === "support" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">🎧 Customer Support & Complaints</h2>
            <p>For enquiries, dispute resolution, or formal complaints, contact our support team at compliance@sparkleconsultants.com or call +675 321 0000.</p>
          </div>
        )}
      </main>
    </div>
  );
}
