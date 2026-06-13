import { Outlet } from "react-router-dom";

import { AdminSideRail } from "@/components/layout/AdminSideRail";
import { Footer } from "@/components/layout/Footer";

export function AdminLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas-warm">
      <div className="flex flex-1 flex-col lg:flex-row">
        <AdminSideRail />
        <main className="flex-1 px-4 py-6 md:px-8 md:py-10">
          <div className="mx-auto w-full max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
      <Footer />
    </div>
  );
}
