import { useState } from "react";
import { login } from "../../lib/api";

export default function PublicSite({ onLoginSuccess, onNavigateToApply }) {
  const [activeTab, setActiveTab] = useState("home");

  // Calculator state
  const [calcAmount, setCalcAmount] = useState(2000);
  const [calcTerm, setCalcTerm] = useState(10);
  const [calcPeriod, setCalcPeriod] = useState("fortnightly");
  const [calcResult, setCalcResult] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);

  // Login form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

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
      await login(email, password);
      onLoginSuccess();
    } catch (err) {
      setLoginError(err.message || "Invalid credentials.");
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
              { id: "loans", label: "Loans" },
              { id: "calculator", label: "Calculator" },
              { id: "how_it_works", label: "How It Works" },
              { id: "eligibility", label: "Eligibility" },
              { id: "faqs", label: "FAQs" },
              { id: "about", label: "About" },
              { id: "contact", label: "Contact" },
              { id: "responsible", label: "Responsible Lending" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-2 rounded transition-colors ${
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
                  Sparkle Consultants provides 100% online loan applications, automated credit decisioning, and direct BSP payment disbursements across all provinces.
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
                    Calculate My Repayment
                  </button>
                </div>
              </div>
            </section>

            {/* Key Benefits Grid */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm">
                <div className="text-3xl mb-3">⚡</div>
                <h3 className="font-display text-lg font-bold text-kina-deep uppercase">Instant Decision</h3>
                <p className="text-xs text-ledger-ink/70 mt-2">
                  Our automated decision engine evaluates your application in real-time with no branch queues or physical paperwork.
                </p>
              </div>
              <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm">
                <div className="text-3xl mb-3">🏦</div>
                <h3 className="font-display text-lg font-bold text-kina-deep uppercase">Direct Bank Credit</h3>
                <p className="text-xs text-ledger-ink/70 mt-2">
                  Approved funds are disbursed directly to your BSP or PNG commercial bank account.
                </p>
              </div>
              <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm">
                <div className="text-3xl mb-3">🛡️</div>
                <h3 className="font-display text-lg font-bold text-kina-deep uppercase">Alesco & DTI Protection</h3>
                <p className="text-xs text-ledger-ink/70 mt-2">
                  Public servant deduction ceiling checks and strict debt-to-income limits ensure safe, responsible borrowing.
                </p>
              </div>
            </section>
          </div>
        )}

        {/* Loan Calculator Surface */}
        {activeTab === "calculator" && (
          <div className="bg-white p-6 md:p-8 border border-ledger-rule rounded shadow-sm max-w-3xl mx-auto space-y-6">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">
              🧮 Interactive Loan Calculator
            </h2>
            <p className="text-xs text-ledger-ink/70">
              Calculate your exact fortnightly or monthly repayment using our server-side financial engine.
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
                  min="200"
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

        {/* Public Information Pages */}
        {activeTab === "how_it_works" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-3xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">How It Works</h2>
            <ol className="list-decimal pl-5 space-y-3 text-sm">
              <li><strong>Create Account & Self-Register:</strong> Enter your basic personal details and mobile phone number.</li>
              <li><strong>Fill Online 17-Step Wizard:</strong> Provide income, employment details, and bank account details.</li>
              <li><strong>Automated Assessment:</strong> Our credit engine instantly evaluates your application against risk and DTI limits.</li>
              <li><strong>E-Sign Digital Contract:</strong> Review your loan offer and electronically sign the binding agreement.</li>
              <li><strong>Direct Disbursement:</strong> Funds are sent straight to your BSP bank account.</li>
            </ol>
          </div>
        )}

        {activeTab === "eligibility" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-3xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Eligibility Requirements</h2>
            <ul className="list-disc pl-5 space-y-2 text-sm">
              <li>Must be a Papua New Guinea citizen or registered resident aged 18+.</li>
              <li>Must have a verifiable fortnightly income of at least PGK 300.</li>
              <li>Must hold an active bank account with BSP, Kina Bank, or Westpac PNG.</li>
              <li>Public service employees must comply with Alesco 50% net pay retention rules.</li>
            </ul>
          </div>
        )}

        {activeTab === "faqs" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-3xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Frequently Asked Questions</h2>
            <div className="space-y-3 text-sm">
              <p><strong>Q: How long does approval take?</strong><br />A: Automated decisions are issued within seconds of submitting your application.</p>
              <p><strong>Q: What payment methods are supported?</strong><br />A: BSP online gateway, bank transfer, and payroll deduction.</p>
            </div>
          </div>
        )}

        {activeTab === "about" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-3xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">About Sparkle Consultants</h2>
            <p className="text-sm">Sparkle Consultants is a premier single-business online lending platform delivering transparent, technology-driven micro-financing across Papua New Guinea.</p>
          </div>
        )}

        {activeTab === "contact" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-3xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Contact Us</h2>
            <p className="text-sm">Email: owner@sparkleconsultants.com<br />Phone: +675 321 0000<br />Address: Waigani, Port Moresby, NCD, Papua New Guinea</p>
          </div>
        )}

        {activeTab === "responsible" && (
          <div className="bg-white p-8 border border-ledger-rule rounded max-w-3xl mx-auto space-y-4 text-xs leading-relaxed">
            <h2 className="text-2xl font-display font-bold uppercase text-kina-deep">Responsible Lending Policy</h2>
            <p className="text-sm">Sparkle Consultants strictly enforces debt-to-income limits and Alesco payroll retention caps to prevent over-indebtedness.</p>
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
