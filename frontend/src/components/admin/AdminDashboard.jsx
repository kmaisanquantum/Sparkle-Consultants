import { useState, useEffect } from "react";

export default function AdminDashboard({ onLogout }) {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [metrics, setMetrics] = useState(null);
  const [customersList, setCustomersList] = useState([]);
  const [applicationsList, setApplicationsList] = useState([]);
  const [collectionsList, setCollectionsList] = useState([]);
  const [auditLogsList, setAuditLogsList] = useState([]);
  const [productsList, setProductsList] = useState([]);
  const [settingsList, setSettingsList] = useState([]);
  const [usersList, setUsersList] = useState([]);

  // Product edit form state
  const [editingProduct, setEditingProduct] = useState(null);
  const [prodForm, setProdForm] = useState({
    code: "", name: "", min_amount: 100, max_amount: 50000, interest_rate_bp: 1500, admin_fee: 50, max_dti_pct: 50
  });

  // User management form state
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({
    email: "", password: "", role: "administrator", full_name: "", is_active: true
  });
  const [userFormError, setUserFormError] = useState("");

  // Dedicated Password Reset Modal state
  const [resetModalUser, setResetModalUser] = useState(null);
  const [newPasswordVal, setNewPasswordVal] = useState("");
  const [resetMsg, setResetMsg] = useState("");

  const fetchUsers = async () => {
    const token = localStorage.getItem("sparkle_token");
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const res = await fetch("/api/v1/admin/users", { headers });
      if (res.ok) {
        const data = await res.json();
        setUsersList(data);
      }
    } catch (e) {
      console.error("Error fetching users:", e);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("sparkle_token");
    const headers = { Authorization: `Bearer ${token}` };

    fetch("/api/v1/admin/metrics", { headers }).then(res => res.json()).then(setMetrics).catch(console.error);
    fetch("/api/v1/admin/customers", { headers }).then(res => res.json()).then(setCustomersList).catch(console.error);
    fetch("/api/v1/admin/applications", { headers }).then(res => res.json()).then(setApplicationsList).catch(console.error);
    fetch("/api/v1/admin/collections", { headers }).then(res => res.json()).then(setCollectionsList).catch(console.error);
    fetch("/api/v1/admin/audit-logs", { headers }).then(res => res.json()).then(setAuditLogsList).catch(console.error);
    fetch("/api/v1/products/admin/all", { headers }).then(res => res.json()).then(data => { if (Array.isArray(data)) setProductsList(data); }).catch(console.error);
    fetch("/api/v1/admin/settings", { headers }).then(res => res.json()).then(data => { if (Array.isArray(data)) setSettingsList(data); }).catch(console.error);
    fetchUsers();
  }, []);

  const handleExportReport = (format) => {
    const token = localStorage.getItem("sparkle_token");
    window.open(`/api/v1/reports/export?format=${format}&token=${token}`, "_blank");
  };

  const handleSaveProduct = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("sparkle_token");
    const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
    try {
      if (editingProduct?.id) {
        await fetch(`/api/v1/products/${editingProduct.id}`, {
          method: "PUT",
          headers,
          body: JSON.stringify(prodForm)
        });
      } else {
        await fetch("/api/v1/products", {
          method: "POST",
          headers,
          body: JSON.stringify(prodForm)
        });
      }
      alert("Loan Product saved successfully!");
      const res = await fetch("/api/v1/products/admin/all", { headers });
      const data = await res.json();
      if (Array.isArray(data)) setProductsList(data);
      setEditingProduct(null);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    setUserFormError("");
    const token = localStorage.getItem("sparkle_token");
    const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

    try {
      if (editingUser?.id) {
        const res = await fetch(`/api/v1/admin/users/${editingUser.id}`, {
          method: "PATCH",
          headers,
          body: JSON.stringify({
            full_name: userForm.full_name,
            role: userForm.role,
            is_active: userForm.is_active,
            password: userForm.password ? userForm.password : undefined
          })
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "Failed to update user");
        }
      } else {
        const res = await fetch("/api/v1/admin/users", {
          method: "POST",
          headers,
          body: JSON.stringify({
            email: userForm.email,
            password: userForm.password,
            role: userForm.role,
            full_name: userForm.full_name
          })
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "Failed to create user");
        }
      }
      await fetchUsers();
      setShowUserModal(false);
      setEditingUser(null);
    } catch (err) {
      setUserFormError(err.message);
    }
  };

  const handleTriggerResetPassword = async (e) => {
    e.preventDefault();
    setResetMsg("");
    const token = localStorage.getItem("sparkle_token");
    const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

    try {
      const res = await fetch(`/api/v1/admin/users/${resetModalUser.id}/reset-password`, {
        method: "POST",
        headers,
        body: JSON.stringify({ password: newPasswordVal })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to reset password");
      }
      setResetMsg("✅ Password reset successfully!");
      setTimeout(() => {
        setResetModalUser(null);
        setNewPasswordVal("");
        setResetMsg("");
      }, 1500);
    } catch (err) {
      setResetMsg(`⚠️ Error: ${err.message}`);
    }
  };

  const handleDeactivateUser = async (userId, userEmail) => {
    if (!confirm(`Are you sure you want to deactivate or delete user ${userEmail}?`)) return;
    const token = localStorage.getItem("sparkle_token");
    const headers = { Authorization: `Bearer ${token}` };

    try {
      const res = await fetch(`/api/v1/admin/users/${userId}`, { method: "DELETE", headers });
      if (!res.ok) {
        const errData = await res.json();
        alert(`Error: ${errData.detail}`);
        return;
      }
      await fetchUsers();
    } catch (err) {
      console.error(err);
    }
  };

  const adminModules = [
    { id: "dashboard", label: "📊 Overview & Metrics" },
    { id: "users", label: "👤 User Management" },
    { id: "customers", label: "👥 Customers & Risk" },
    { id: "applications", label: "📝 Applications" },
    { id: "collections", label: "🚨 Collections & Arrears" },
    { id: "products", label: "⚙️ Editable Loan Products" },
    { id: "compliance", label: "🛡️ Immutable Audit Logs" },
    { id: "reports", label: "📈 Portfolio Export Reports" },
    { id: "settings", label: "🔧 Editable System Settings" },
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
          <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-3 py-1 rounded">RBAC Guarded Active</span>
        </header>

        {/* 1. Overview Dashboard */}
        {activeModule === "dashboard" && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Total Customers</span>
                <p className="text-2xl font-bold text-kina-deep mt-1">{metrics?.total_customers || 0}</p>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Active Loans</span>
                <p className="text-2xl font-bold text-kina-deep mt-1">{metrics?.active_loans || 0}</p>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Disbursed Total</span>
                <p className="text-2xl font-bold text-kina-gold mt-1">PGK {(metrics?.disbursed_totals || 0).toLocaleString()}</p>
              </div>
              <div className="bg-white p-5 border border-ledger-rule rounded shadow-sm">
                <span className="text-xs text-ledger-ink/60 font-display uppercase">Repayments Received</span>
                <p className="text-2xl font-bold text-emerald-600 mt-1">PGK {(metrics?.repayments_received || 0).toLocaleString()}</p>
              </div>
            </div>

            {/* Arrears Buckets Breakdown */}
            <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-3">
              <h3 className="font-display text-base font-bold text-kina-deep uppercase">🚨 Arrears Stage Breakdown</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                  <span className="text-yellow-800 font-bold">1 - 7 Days Overdue:</span>
                  <p className="text-lg font-bold">{metrics?.arrears_buckets?.["1_7_days"] || 0} accounts</p>
                </div>
                <div className="p-3 bg-orange-50 border border-orange-200 rounded">
                  <span className="text-orange-800 font-bold">8 - 30 Days Overdue:</span>
                  <p className="text-lg font-bold">{metrics?.arrears_buckets?.["8_30_days"] || 0} accounts</p>
                </div>
                <div className="p-3 bg-red-50 border border-red-200 rounded">
                  <span className="text-red-800 font-bold">31 - 60 Days Overdue:</span>
                  <p className="text-lg font-bold">{metrics?.arrears_buckets?.["31_60_days"] || 0} accounts</p>
                </div>
                <div className="p-3 bg-purple-50 border border-purple-200 rounded">
                  <span className="text-purple-800 font-bold">60+ Days (Recovery):</span>
                  <p className="text-lg font-bold">{metrics?.arrears_buckets?.["60_plus_days"] || 0} accounts</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 2. User Management Module */}
        {activeModule === "users" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-6 text-xs">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-display font-bold text-lg text-kina-deep uppercase">User Management Directory</h3>
                <p className="text-ledger-ink/60">Create, edit roles, reset passwords, and activate/deactivate platform users.</p>
              </div>
              <button
                onClick={() => {
                  setEditingUser(null);
                  setUserForm({ email: "", password: "", role: "administrator", full_name: "", is_active: true });
                  setUserFormError("");
                  setShowUserModal(true);
                }}
                className="px-4 py-2 bg-kina-gold text-kina-deep font-display font-bold uppercase rounded shadow hover:bg-yellow-400"
              >
                + Create User
              </button>
            </div>

            {/* Modal for User Create/Edit */}
            {showUserModal && (
              <div className="p-4 bg-ledger-paper border border-ledger-rule rounded space-y-3">
                <h4 className="font-bold text-kina-deep uppercase">{editingUser ? "Edit User Account" : "Create New User"}</h4>
                {userFormError && <div className="p-2 bg-red-100 text-red-800 rounded font-bold">⚠️ {userFormError}</div>}

                <form onSubmit={handleSaveUser} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold">Email Address</label>
                    <input
                      type="email"
                      required
                      disabled={!!editingUser}
                      value={userForm.email}
                      onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                      className="w-full p-2 border rounded bg-white disabled:bg-gray-100"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold">Full Name</label>
                    <input
                      type="text"
                      required
                      value={userForm.full_name}
                      onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
                      className="w-full p-2 border rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold">User Role</label>
                    <select
                      value={userForm.role}
                      onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                      className="w-full p-2 border rounded bg-white"
                    >
                      <option value="administrator">Administrator (Full Access)</option>
                      <option value="customer">Customer (Active Borrower)</option>
                      <option value="client">Client (Applicant / Lead)</option>
                      <option value="underwriter">Underwriter</option>
                      <option value="collections_agent">Collections Agent</option>
                      <option value="compliance_officer">Compliance Officer</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold">{editingUser ? "New Password (Optional)" : "Password"}</label>
                    <input
                      type="password"
                      required={!editingUser}
                      value={userForm.password}
                      onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                      className="w-full p-2 border rounded bg-white"
                      placeholder={editingUser ? "Leave blank to keep existing" : "••••••••"}
                    />
                  </div>
                  {editingUser && (
                    <div className="sm:col-span-2 flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="is_active_chk"
                        checked={userForm.is_active}
                        onChange={(e) => setUserForm({ ...userForm, is_active: e.target.checked })}
                      />
                      <label htmlFor="is_active_chk" className="font-semibold">Account Active</label>
                    </div>
                  )}
                  <div className="sm:col-span-2 flex justify-end space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowUserModal(false)}
                      className="px-4 py-2 border rounded font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-kina-deep text-ledger-paper font-bold uppercase rounded"
                    >
                      {editingUser ? "Update User" : "Create User"}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Modal for Dedicated Password Reset */}
            {resetModalUser && (
              <div className="p-4 bg-yellow-50 border border-yellow-300 rounded space-y-3">
                <h4 className="font-bold text-kina-deep uppercase">🔑 Reset Password for {resetModalUser.email}</h4>
                {resetMsg && <div className="text-xs font-bold">{resetMsg}</div>}

                <form onSubmit={handleTriggerResetPassword} className="space-y-3 max-w-md">
                  <div>
                    <label className="block font-semibold mb-1">New Password</label>
                    <input
                      type="password"
                      required
                      value={newPasswordVal}
                      onChange={(e) => setNewPasswordVal(e.target.value)}
                      placeholder="Enter new password"
                      className="w-full p-2 border rounded bg-white"
                    />
                  </div>
                  <div className="flex space-x-2">
                    <button
                      type="submit"
                      className="px-4 py-1.5 bg-kina-deep text-ledger-paper font-bold uppercase rounded"
                    >
                      Confirm Reset
                    </button>
                    <button
                      type="button"
                      onClick={() => setResetModalUser(null)}
                      className="px-4 py-1.5 border rounded font-semibold"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-ledger-rule font-display uppercase text-ledger-ink/60">
                    <th className="py-2">Full Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Created At</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ledger-rule/20">
                  {usersList.map((u) => (
                    <tr key={u.id}>
                      <td className="py-2.5 font-bold">{u.full_name}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                          u.role === 'administrator' || u.role === 'owner' ? 'bg-purple-100 text-purple-800' :
                          u.role === 'customer' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {u.is_active ? "Active" : "Deactivated"}
                        </span>
                      </td>
                      <td className="text-ledger-ink/60">{new Date(u.created_at).toLocaleDateString()}</td>
                      <td className="space-x-2">
                        <button
                          onClick={() => {
                            setEditingUser(u);
                            setUserForm({
                              email: u.email,
                              password: "",
                              role: u.role,
                              full_name: u.full_name,
                              is_active: u.is_active
                            });
                            setUserFormError("");
                            setShowUserModal(true);
                          }}
                          className="px-2 py-0.5 border border-kina-deep text-kina-deep rounded font-bold text-[10px]"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => {
                            setResetModalUser(u);
                            setNewPasswordVal("");
                            setResetMsg("");
                          }}
                          className="px-2 py-0.5 border border-yellow-600 text-yellow-800 rounded font-bold text-[10px]"
                        >
                          Reset Pass
                        </button>
                        {u.is_active && (
                          <button
                            onClick={() => handleDeactivateUser(u.id, u.email)}
                            className="px-2 py-0.5 border border-red-600 text-red-600 rounded font-bold text-[10px]"
                          >
                            Deactivate
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 3. Customers Module */}
        {activeModule === "customers" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">Customer Directory & Risk Flags</h3>
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

        {/* 4. Editable Loan Products */}
        {activeModule === "products" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-6 text-xs">
            <div className="flex justify-between items-center">
              <h3 className="font-display font-bold text-lg text-kina-deep uppercase">Loan Products Configurator</h3>
              <button
                onClick={() => {
                  setEditingProduct({});
                  setProdForm({ code: "NEW_PROD", name: "New Product", min_amount: 500, max_amount: 10000, interest_rate_bp: 1500, admin_fee: 50, max_dti_pct: 50 });
                }}
                className="px-3 py-1.5 bg-kina-gold text-kina-deep font-display font-bold uppercase rounded shadow"
              >
                + Create Loan Product
              </button>
            </div>

            {editingProduct && (
              <form onSubmit={handleSaveProduct} className="p-4 bg-ledger-paper border border-ledger-rule rounded space-y-3">
                <h4 className="font-bold text-kina-deep uppercase">Edit Product Details</h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <label className="block font-semibold">Product Code</label>
                    <input type="text" value={prodForm.code} onChange={(e) => setProdForm({ ...prodForm, code: e.target.value })} className="w-full p-1 border rounded" />
                  </div>
                  <div>
                    <label className="block font-semibold">Name</label>
                    <input type="text" value={prodForm.name} onChange={(e) => setProdForm({ ...prodForm, name: e.target.value })} className="w-full p-1 border rounded" />
                  </div>
                  <div>
                    <label className="block font-semibold">Interest Rate BP</label>
                    <input type="number" value={prodForm.interest_rate_bp} onChange={(e) => setProdForm({ ...prodForm, interest_rate_bp: parseInt(e.target.value) })} className="w-full p-1 border rounded" />
                  </div>
                  <div>
                    <label className="block font-semibold">Admin Fee (PGK)</label>
                    <input type="number" value={prodForm.admin_fee} onChange={(e) => setProdForm({ ...prodForm, admin_fee: parseFloat(e.target.value) })} className="w-full p-1 border rounded" />
                  </div>
                </div>
                <button type="submit" className="px-4 py-1.5 bg-kina-deep text-ledger-paper rounded font-bold uppercase">Save Product</button>
              </form>
            )}

            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-ledger-rule font-display uppercase text-ledger-ink/60">
                  <th className="py-2">Code</th>
                  <th>Name</th>
                  <th>Min - Max Amount</th>
                  <th>Interest Rate</th>
                  <th>Admin Fee</th>
                  <th>Max DTI</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ledger-rule/20">
                {productsList.map((p) => (
                  <tr key={p.id}>
                    <td className="py-2.5 font-bold font-mono">{p.code}</td>
                    <td>{p.name}</td>
                    <td>PGK {p.min_amount} - {p.max_amount}</td>
                    <td>{(p.interest_rate_bp / 100).toFixed(2)}%</td>
                    <td>PGK {p.admin_fee}</td>
                    <td>{p.max_dti_pct}%</td>
                    <td>
                      <button
                        onClick={() => {
                          setEditingProduct(p);
                          setProdForm({ code: p.code, name: p.name, min_amount: p.min_amount, max_amount: p.max_amount, interest_rate_bp: p.interest_rate_bp, admin_fee: p.admin_fee, max_dti_pct: p.max_dti_pct });
                        }}
                        className="px-2 py-0.5 border border-kina-deep text-kina-deep rounded font-bold"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 5. Portfolio Reports Export */}
        {activeModule === "reports" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">Portfolio Reports & Statement Exports</h3>
            <p>Export full loan portfolio summaries directly into CSV, Excel, or PDF report formats.</p>
            <div className="flex gap-4 pt-2">
              <button onClick={() => handleExportReport("csv")} className="px-4 py-2 bg-kina-deep text-ledger-paper font-display uppercase font-bold rounded shadow">
                📄 Export CSV
              </button>
              <button onClick={() => handleExportReport("excel")} className="px-4 py-2 bg-emerald-700 text-white font-display uppercase font-bold rounded shadow">
                📊 Export Excel (.xlsx)
              </button>
              <button onClick={() => handleExportReport("pdf")} className="px-4 py-2 bg-red-700 text-white font-display uppercase font-bold rounded shadow">
                📕 Export PDF Summary
              </button>
            </div>
          </div>
        )}

        {/* 6. Compliance & Audit Module */}
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

        {/* Applications & Collections Retained */}
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

        {activeModule === "settings" && (
          <div className="bg-white p-6 border border-ledger-rule rounded shadow-sm space-y-4 text-xs">
            <h3 className="font-display font-bold text-lg text-kina-deep uppercase">System Settings Control Panel</h3>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-ledger-rule font-display uppercase text-ledger-ink/60">
                  <th className="py-2">Key</th>
                  <th>Value</th>
                  <th>Category</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ledger-rule/20 font-mono">
                {settingsList.map((s) => (
                  <tr key={s.id}>
                    <td className="py-2 font-bold">{s.key}</td>
                    <td>{s.value}</td>
                    <td>{s.category}</td>
                    <td className="font-sans">{s.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
