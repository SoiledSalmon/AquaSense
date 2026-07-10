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
  return res.json();
}

export async function getAlerts(
  status:
    | "all"
    | "unread"
    | "unacknowledged"
    | "resolved"
    | "active" = "unacknowledged",
  limit = 50,
) {
  const headers = await getHeaders();
  const res = await fetch(
    `${API_URL}/api/alerts?status=${status}&limit=${limit}`,
    {
      method: "GET",
      headers,
      cache: "no-store",
      credentials: "include",
    },
  );
  return handleResponse(res);
}

export async function acknowledgeAlert(alertId: string) {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/alerts/${alertId}/acknowledge`, {
    method: "POST",
    headers,
    credentials: "include",
  });
  return handleResponse(res);
}

export async function resolveAlert(alertId: string) {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/alerts/${alertId}/resolve`, {
    method: "POST",
    headers,
    credentials: "include",
  });
  return handleResponse(res);
}

export async function readAlert(alertId: string) {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/alerts/${alertId}/read`, {
    method: "POST",
    headers,
    credentials: "include",
  });
  return handleResponse(res);
}
