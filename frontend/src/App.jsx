import { useState, useEffect } from "react";
import PublicSite from "./components/public/PublicSite.jsx";
import CustomerPortal from "./components/customer/CustomerPortal.jsx";
import AdminDashboard from "./components/admin/AdminDashboard.jsx";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("sparkle_token"));
  const [userRole, setUserRole] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkUserRole = async () => {
      const storedToken = localStorage.getItem("sparkle_token");
      if (!storedToken) {
        setUserRole(null);
        setLoading(false);
        return;
      }
      try {
        const res = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${storedToken}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUserRole(data.role);
        } else {
          localStorage.removeItem("sparkle_token");
          setToken(null);
          setUserRole(null);
        }
      } catch (err) {
        console.error("Auth me check error:", err);
      } finally {
        setLoading(false);
      }
    };

    checkUserRole();
  }, [token]);

  const handleLoginSuccess = () => {
    const freshToken = localStorage.getItem("sparkle_token");
    setToken(freshToken);
  };

  const handleLogout = () => {
    localStorage.removeItem("sparkle_token");
    setToken(null);
    setUserRole(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-ledger-paper flex items-center justify-center font-display text-lg text-kina-deep">
        ✨ Sparkle Consultants Platform Loading…
      </div>
    );
  }

  // Render surface based on auth role:
  // - Administrator & Staff roles (administrator, admin, owner, underwriter, collections_agent, compliance_officer) -> AdminDashboard
  // - Customer & Client roles (customer, client) -> CustomerPortal
  if (token && userRole) {
    if (["administrator", "admin", "owner", "underwriter", "collections_agent", "compliance_officer"].includes(userRole)) {
      return <AdminDashboard onLogout={handleLogout} />;
    }
    return <CustomerPortal onLogout={handleLogout} />;
  }

  // Default: Public Website surface
  return <PublicSite onLoginSuccess={handleLoginSuccess} />;
}
