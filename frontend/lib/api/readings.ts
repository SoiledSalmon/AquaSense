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

export async function getLatestReading() {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/readings/latest`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}

export async function getReadingsHistory(range: "24h" | "7d" | "30d") {
  const headers = await getHeaders();
  const res = await fetch(`${API_URL}/api/readings?range=${range}`, {
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "include",
  });
  return handleResponse(res);
}

export function getSSEStreamUrl() {
  return `${API_URL}/api/stream`;
}
