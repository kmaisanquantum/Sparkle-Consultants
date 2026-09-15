import { useState, useEffect } from "react";
import { login } from "../../lib/api";

export default function PublicSite({ onLoginSuccess, onNavigateToApply }) {
  const [activeTab, setActiveTab] = useState("home");
  const [products, setProducts] = useState([]);

  // Calculator state
  const [calcAmount, setCalcAmount] = useState(2000);
  const [calcTerm, setCalcTerm] = useState(10);
  const [calcPeriod, setCalcPeriod] = useState("fortnightly");
  const [calcResult, setCalcResult] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);

  // Login form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  useEffect(() => {
    fetch("/api/v1/products")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setProducts(data);
      })
      .catch((err) => console.error("Error loading products:", err));
  }, []);

  const handleCalculate = async (e) => {
    if (e) e.preventDefault();
    setCalcLoading(true);
    try {
      const res = await fetch("/api/v1/calculator", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          principal_amount: parseFloat(calcAmount),
          interest_rate_bp: 1500,
          compounding_period: calcPeriod,
          term_periods: parseInt(calcTerm),
          admin_fee: 50.0
        })
      });
      if (res.ok) {
        const data = await res.json();
        setCalcResult(data);
      }
    } catch (err) {
      console.error("Calculator error:", err);
    } finally {
      setCalcLoading(false);
    }
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);
    try {
      await login(email, password, mfaCode);
      onLoginSuccess();
    } catch (err) {
      if (err.message && err.message.includes("MFA code required")) {
        setMfaRequired(true);
        setLoginError("MFA code required. Please enter your authenticator token.");
      } else {
        setLoginError(err.message || "Invalid credentials.");
      }
    } finally {
      setLoginLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ledger-paper font-sans text-ledger-ink flex flex-col">
      {/* Top Header Navigation */}
      <header className="bg-kina-deep text-ledger-paper sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab("home")}>
            <span className="text-2xl">✨</span>
            <div>
              <h1 className="font-display text-lg font-bold uppercase tracking-wider text-kina-gold">
                Sparkle Consultants
              </h1>
              <p className="text-[10px] text-ledger-paper/70 tracking-widest uppercase">
                A fully online lending service for PNG
              </p>
            </div>
          </div>

          <nav className="hidden md:flex space-x-1 text-xs font-display uppercase tracking-wider font-semibold">
            {[
              { id: "home", label: "Home" },
              { id: "loans", label: "Products & Rates" },
              { id: "calculator", label: "Calculator" },
              { id: "terms", label: "Terms & Conditions" },
              { id: "privacy", label: "Privacy Policy" },
              { id: "responsible", label: "Responsible Lending" },
              { id: "complaints", label: "Complaints & Disputes" },
              { id: "collections", label: "Default & Collections" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-2.5 py-1.5 rounded transition-colors ${
                  activeTab === tab.id
                    ? "bg-kina-gold text-kina-deep font-bold"
                    : "hover:bg-white/10 text-ledger-paper/90"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setActiveTab("login")}
              className="px-3 py-1.5 text-xs font-display uppercase font-semibold border border-kina-gold/60 text-kina-gold rounded hover:bg-kina-gold/10"
            >
              Sign In
            </button>
            <button
              onClick={() => {
                if (onNavigateToApply) onNavigateToApply();
                else setActiveTab("calculator");
              }}
              className="px-4 py-1.5 text-xs font-display uppercase font-bold bg-kina-gold text-kina-deep rounded shadow hover:bg-yellow-400"
            >
              Apply Now
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Surfaces */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === "home" && (
          <div className="space-y-12">
            {/* Hero Section */}
            <section className="bg-gradient-to-r from-kina-deep to-teal-900 text-ledger-paper rounded-lg p-8 md:p-12 shadow-lg">
              <div className="max-w-3xl space-y-6">
                <span className="inline-block bg-kina-gold/20 text-kina-gold border border-kina-gold/40 px-3 py-1 rounded-full text-xs font-display uppercase tracking-widest">
                  PNG Digital Micro-Lending Platform
                </span>
                <h1 className="text-3xl md:text-5xl font-display font-bold text-kina-gold tracking-wide leading-tight">
                  Fast, Transparent, Online Loans for Papua New Guinea
                </h1>
                <p className="text-base md:text-lg text-ledger-paper/85 leading-relaxed">
                  Sparkle Consultants provides 100% online loan applications, automated credit decisioning, and direct BSP payment disbursements across all PNG provinces.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 pt-4">
                  <button
                    onClick={() => {
                      if (onNavigateToApply) onNavigateToApply();
                      else setActiveTab("calculator");
                    }}
                    className="px-6 py-3 bg-kina-gold text-kina-deep font-display font-bold uppercase tracking-wider rounded shadow-md hover:bg-yellow-400 text-center"
                  >
                    Apply For A Loan
                  </button>
                  <button
                    onClick={() => setActiveTab("calculator")}
                    className="px-6 py-3 border border-ledger-paper/40 font-display font-bold uppercase tracking-wider rounded hover:bg-white/10 text-center"
                  >
                    Calculate Repayment
                  </button>
                </div>
              </div>
            </section>

            {/* Key Benefits Grid */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm">
                <div className="text-3xl mb-3">⚡</div>
                <h3 className="font-display text-lg font-bold text-kina-deep uppercase">Instant Credit Assessment</h3>
                <p className="text-xs text-ledger-ink/70 mt-2">
                  Automated decisioning evaluates your credit score, fortnightly income, and DTI metrics without physical branch queues.
                </p>
              </div>
              <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm">
                <div className="text-3xl mb-3">🏦</div>
                <h3 className="font-display text-lg font-bold text-kina-deep uppercase">Direct Bank Credit</h3>
                <p className="text-xs text-ledger-ink/70 mt-2">
                  Approved loan principal is disbursed directly to your BSP or commercial bank account in PGK.
                </p>
              </div>
              <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm">
                <div className="text-3xl mb-3">🛡️</div>
                <h3 className="font-display text-lg font-bold text-kina-deep uppercase">Alesco & DTI Consumer Protection</h3>
                <p className="text-xs text-ledger-ink/70 mt-2">
                  Public service 50% net pay retention caps and strict debt-to-income limits ensure safe, sustainable micro-borrowing.
                </p>
              </div>
            </section>
          </div>
        )}

        {/* Loan Products & Rates Page */}
        {activeTab === "loans" && (
          <div className="bg-white p-6 md:p-8 border border-ledger-rule rounded shadow-sm space-y-6">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">
              🏷️ Active Loan Products & Interest Rates
            </h2>
            <p className="text-xs text-ledger-ink/70">
              Live rate card pulled directly from configured system products. All fees and limits are fully transparent.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {products.map((p) => (
                <div key={p.id} className="border border-ledger-rule p-5 rounded bg-ledger-paper/30 space-y-3">
                  <div className="flex justify-between items-center">
                    <h3 className="font-display font-bold text-lg text-kina-deep">{p.name}</h3>
                    <span className="text-xs font-mono bg-kina-gold/20 text-kina-deep px-2 py-0.5 rounded font-bold">
                      {p.code}
                    </span>
                  </div>
                  <p className="text-xs text-ledger-ink/80">{p.description || "Standard automated micro-loan product."}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-ledger-rule/50">
                    <div><strong>Min - Max Amount:</strong> PGK {p.min_amount} - PGK {p.max_amount}</div>
                    <div><strong>Interest Rate:</strong> {(p.interest_rate_bp / 100).toFixed(2)}% per period</div>
                    <div><strong>Admin Fee:</strong> PGK {p.admin_fee}</div>
                    <div><strong>Max DTI Cap:</strong> {p.max_dti_pct}%</div>
                    <div><strong>Term Range:</strong> {p.min_term} - {p.max_term} periods</div>
                    <div><strong>Frequency:</strong> {p.compounding_period}</div>
                  </div>
                  <button
                    onClick={() => {
                      if (onNavigateToApply) onNavigateToApply();
                    }}
                    className="w-full mt-3 py-2 bg-kina-deep text-ledger-paper font-display text-xs uppercase font-bold rounded"
                  >
                    Apply For {p.name}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Loan Calculator Surface */}
        {activeTab === "calculator" && (
          <div className="bg-white p-6 md:p-8 border border-ledger-rule rounded shadow-sm max-w-3xl mx-auto space-y-6">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">
              🧮 Interactive Loan Calculator
            </h2>
            <p className="text-xs text-ledger-ink/70">
              Calculate your exact fortnightly or monthly repayment using our financial engine.
            </p>

            <form onSubmit={handleCalculate} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-display uppercase tracking-wider font-semibold text-ledger-ink/80 mb-1">
                  Requested Principal (PGK)
                </label>
                <input
                  type="number"
                  value={calcAmount}
                  onChange={(e) => setCalcAmount(e.target.value)}
                  className="w-full p-2 text-sm border border-ledger-rule rounded"
                  min="100"
                  max="50000"
                />
              </div>
              <div>
                <label className="block text-xs font-display uppercase tracking-wider font-semibold text-ledger-ink/80 mb-1">
                  Term Periods
                </label>
                <input
                  type="number"
                  value={calcTerm}
                  onChange={(e) => setCalcTerm(e.target.value)}
                  className="w-full p-2 text-sm border border-ledger-rule rounded"
                  min="2"
                  max="52"
                />
              </div>
              <div>
                <label className="block text-xs font-display uppercase tracking-wider font-semibold text-ledger-ink/80 mb-1">
                  Pay Frequency
                </label>
                <select
                  value={calcPeriod}
                  onChange={(e) => setCalcPeriod(e.target.value)}
                  className="w-full p-2 text-sm border border-ledger-rule rounded"
                >
                  <option value="weekly">Weekly</option>
                  <option value="fortnightly">Fortnightly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div className="sm:col-span-3">
                <button
                  type="submit"
                  disabled={calcLoading}
                  className="w-full py-2 bg-kina-deep text-ledger-paper font-display uppercase font-semibold rounded hover:bg-kina-deep/90"
                >
                  {calcLoading ? "Calculating..." : "Calculate Repayment"}
                </button>
              </div>
            </form>

            {calcResult && (
              <div className="mt-6 bg-ledger-paper p-4 border border-ledger-rule rounded space-y-3">
                <h4 className="font-display text-sm font-bold text-kina-deep uppercase">Calculation Summary</h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                  <div>
                    <span className="text-ledger-ink/60">Periodic Repayment:</span>
                    <p className="text-base font-bold text-kina-deep">PGK {calcResult.periodic_repayment?.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-ledger-ink/60">Total Repayment:</span>
                    <p className="text-base font-bold text-ledger-ink">PGK {calcResult.total_repayment?.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-ledger-ink/60">Total Interest:</span>
                    <p className="text-base font-bold text-ledger-ink">PGK {calcResult.total_interest?.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-ledger-ink/60">Admin Fee:</span>
                    <p className="text-base font-bold text-ledger-ink">PGK {calcResult.total_fees?.toLocaleString()}</p>
                  </div>
                </div>

                <div className="pt-3">
                  <button
                    onClick={() => {
                      if (onNavigateToApply) onNavigateToApply();
                    }}
                    className="w-full py-2 bg-kina-gold text-kina-deep font-display font-bold uppercase rounded"
                  >
                    Proceed To Online Application
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Consumer Protection Pages */}
        {activeTab === "terms" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-4xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Loan Terms & Conditions</h2>
            <p>Sparkle Consultants provides short-term micro-financing under strict credit policies and PNG consumer protection guidelines.</p>
            <h3 className="font-bold text-sm text-kina-deep">1. Repayment Obligations</h3>
            <p>Borrowers are bound to repay the agreed principal, accrued interest, and administrative fees according to the generated LoanSchedule.</p>
            <h3 className="font-bold text-sm text-kina-deep">2. Payroll Deductions</h3>
            <p>Public servants opting for Alesco payroll deduction consent to direct employer withholding up to the 50% net pay retention ceiling.</p>
            <p className="text-[10px] text-ledger-ink/60 mt-4">[TODO: Verify specific PNG commercial lending licensing updates as regulatory framework evolves.]</p>
          </div>
        )}

        {activeTab === "privacy" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-4xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Privacy & Data Protection Policy</h2>
            <p>We respect your privacy and protect sensitive borrower PII using AES-GCM application-layer encryption and peppered SHA-256 hashes.</p>
            <h3 className="font-bold text-sm text-kina-deep">Data Retention & Deletion</h3>
            <p>Borrower records and audit logs are retained in accordance with financial record-keeping standards for audit compliance. Access to sensitive PII is logged via our AuditService.</p>
          </div>
        )}

        {activeTab === "responsible" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-4xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Responsible Lending Policy</h2>
            <p>Sparkle Consultants conducts automated affordability checks on every application. We cap debt-to-income (DTI) ratios at 50% and enforce Alesco payroll ceilings to prevent debt stress.</p>
          </div>
        )}

        {activeTab === "complaints" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-4xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Complaints & Dispute Resolution</h2>
            <p>If you have a concern regarding fees, service delivery, or collections conduct, submit a complaint via your Customer Portal or email compliance@sparkleconsultants.com.</p>
          </div>
        )}

        {activeTab === "collections" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-4xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Default & Collections Policy</h2>
            <p>In the event of missed repayments, accounts enter structured collection stages (Overdue 1-7 days to Recovery). Arrears notifications will be issued via SMS/in-app messaging. Late fees are calculated per configured product terms.</p>
          </div>
        )}

        {/* Login Surface */}
        {activeTab === "login" && (
          <div className="max-w-md mx-auto bg-white p-8 border border-ledger-rule rounded shadow-sm space-y-6">
            <div className="text-center">
              <span className="text-3xl">🔑</span>
              <h2 className="text-2xl font-display font-bold text-kina-deep uppercase">Sparkle Consultants Login</h2>
              <p className="text-xs text-ledger-ink/60">Sign in to Customer Portal or Admin Dashboard</p>
            </div>

            <form onSubmit={handleLoginSubmit} className="space-y-4">
              {loginError && (
                <div className="p-3 bg-red-50 border border-red-300 text-red-700 text-xs rounded">
                  ⚠️ {loginError}
                </div>
              )}
              <div>
                <label className="block text-xs font-display uppercase tracking-wider font-semibold text-ledger-ink/80 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. owner@sparkleconsultants.com"
                  className="w-full p-2 text-sm border border-ledger-rule rounded bg-ledger-paper/50"
                />
              </div>
              <div>
                <label className="block text-xs font-display uppercase tracking-wider font-semibold text-ledger-ink/80 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full p-2 text-sm border border-ledger-rule rounded bg-ledger-paper/50"
                />
              </div>
              {mfaRequired && (
                <div>
                  <label className="block text-xs font-display uppercase tracking-wider font-semibold text-ledger-ink/80 mb-1">
                    TOTP MFA Code
                  </label>
                  <input
                    type="text"
                    required
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
                    placeholder="6-digit MFA Code"
                    className="w-full p-2 text-sm border border-ledger-rule rounded bg-ledger-paper/50"
                  />
                </div>
              )}
              <button
                type="submit"
                disabled={loginLoading}
                className="w-full py-2 bg-kina-deep text-ledger-paper font-display uppercase font-semibold text-sm rounded shadow hover:bg-kina-deep/90 disabled:opacity-50"
              >
                {loginLoading ? "Authenticating..." : "Sign In"}
              </button>
            </form>

            <div className="pt-4 border-t border-ledger-rule text-center text-xs text-ledger-ink/60">
              Seed Owner Credentials: <code className="bg-ledger-paper px-1 py-0.5 rounded">owner@sparkleconsultants.com</code> / <code className="bg-ledger-paper px-1 py-0.5 rounded">password123</code>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-kina-deep text-ledger-paper/70 py-6 border-t border-ledger-rule/30 text-center text-xs">
        <p>© {new Date().getFullYear()} Sparkle Consultants. A fully online lending service for Papua New Guinea.</p>
      </footer>
    </div>
  );
}
