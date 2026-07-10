const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getHeaders() {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (typeof window === "undefined") {
    try {
      const { cookies } = await import("next/headers");
      const cookieStore = await cookies();
      const cookieString = cookieStore.toString();
      if (cookieString) {
        headers["Cookie"] = cookieString;
      }
    } catch {
      // Ignore: cookies() can only be called in request context
    }
  }

  return headers;
}

async function handleResponse(res: Response) {
  if (!res.ok) {
    let errorMsg = "An error occurred";
    try {
      const data = await res.json();
      errorMsg = data.message || data.error || errorMsg;
    } catch {
      // Fallback
    }
    throw new Error(errorMsg);
  }
  if (res.status === 204) {
    return null;
  }
  return res.json();
}

export async function getAdminStats() {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/admin/stats`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}

export interface GetUsersParams {
  search?: string;
  role?: string;
  sortBy?: string;
  order?: string;
  page?: number;
  limit?: number;
}

export async function getAdminUsers(params: GetUsersParams = {}) {
  const headers = await getHeaders();
  const query = new URLSearchParams();
  if (params.search) query.append("search", params.search);
  if (params.role) query.append("role", params.role);
  if (params.sortBy) query.append("sort_by", params.sortBy);
  if (params.order) query.append("order", params.order);
  if (params.page) query.append("page", params.page.toString());
  if (params.limit) query.append("limit", params.limit.toString());

  const res = await fetch(`${API_URL}/api/admin/users?${query.toString()}`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}

export async function getAdminUser(userId: string) {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/admin/users/${userId}`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}

export async function updateUserRole(userId: string, role: "user" | "admin") {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/admin/users/${userId}/role`, {
    method: "PATCH",
    headers,
    body: JSON.stringify({ role }),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function deleteUser(userId: string) {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/admin/users/${userId}`, {
    method: "DELETE",
    headers,
    credentials: "include",
  });
  return handleResponse(res);
}

export interface GetReadingsParams {
  userId?: string;
  label?: string;
  page?: number;
  limit?: number;
}

export async function getAdminReadings(params: GetReadingsParams = {}) {
  const headers = await getHeaders();
  const query = new URLSearchParams();
  if (params.userId) query.append("user_id", params.userId);
  if (params.label) query.append("label", params.label);
  if (params.page) query.append("page", params.page.toString());
  if (params.limit) query.append("limit", params.limit.toString());

  const res = await fetch(`${API_URL}/api/admin/readings?${query.toString()}`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}

export interface GetAlertsParams {
  userId?: string;
  severity?: string;
  isAcknowledged?: boolean;
  isResolved?: boolean;
  page?: number;
  limit?: number;
}

export async function getAdminAlerts(params: GetAlertsParams = {}) {
  const headers = await getHeaders();
  const query = new URLSearchParams();
  if (params.userId) query.append("user_id", params.userId);
  if (params.severity) query.append("severity", params.severity);
  if (params.isAcknowledged !== undefined)
    query.append("is_acknowledged", params.isAcknowledged.toString());
  if (params.isResolved !== undefined)
    query.append("is_resolved", params.isResolved.toString());
  if (params.page) query.append("page", params.page.toString());
  if (params.limit) query.append("limit", params.limit.toString());

  const res = await fetch(`${API_URL}/api/admin/alerts?${query.toString()}`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}

export interface GetMLParams {
  userId?: string;
  riskLevel?: string;
  isAnomaly?: boolean;
  page?: number;
  limit?: number;
}

export async function getAdminML(params: GetMLParams = {}) {
  const headers = await getHeaders();
  const query = new URLSearchParams();
  if (params.userId) query.append("user_id", params.userId);
  if (params.riskLevel) query.append("risk_level", params.riskLevel);
  if (params.isAnomaly !== undefined)
    query.append("is_anomaly", params.isAnomaly.toString());
  if (params.page) query.append("page", params.page.toString());
  if (params.limit) query.append("limit", params.limit.toString());

  const res = await fetch(`${API_URL}/api/admin/ml?${query.toString()}`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}
