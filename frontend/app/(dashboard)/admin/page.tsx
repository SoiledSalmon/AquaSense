import React from "react";
import { redirect } from "next/navigation";
import { getMe } from "../../../lib/api/auth";
import AdminDashboard from "../../../components/dashboard/AdminDashboard";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Admin Panel | AquaSense",
  description:
    "System-wide telemetry, user management, alerts monitoring, and ML analytics.",
};

export default async function AdminPage() {
  let user = null;
  try {
    user = await getMe();
  } catch (err) {
    redirect("/login?clear=true");
  }

  if (!user || user.role !== "admin") {
    redirect("/dashboard");
  }

  return (
    <div className="space-y-6">
      <AdminDashboard user={user} />
    </div>
  );
}
