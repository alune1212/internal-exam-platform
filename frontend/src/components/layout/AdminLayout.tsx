import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";

import { clearAdminToken, getAdminToken } from "@/lib/adminSession";

import { AdminSideRail } from "@/components/layout/AdminSideRail";

export function AdminLayout() {
  const navigate = useNavigate();

  useEffect(() => {
    if (!getAdminToken()) {
      navigate("/admin/login", { replace: true });
    }
  }, [navigate]);

  function handleLogout() {
    clearAdminToken();
    navigate("/admin/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas-warm">
      <div className="flex flex-1 flex-col lg:flex-row">
        <AdminSideRail onLogout={handleLogout} />
        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
