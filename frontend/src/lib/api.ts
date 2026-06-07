/**
 * API client wrapper for the FastAPI backend.
 */

const API_BASE_URL = "http://localhost:8000/api";

class ApiClient {
  private getToken() {
    if (typeof window !== "undefined") {
      return localStorage.getItem("dsmi_token");
    }
    return null;
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = new Headers(options.headers || {});
    
    // Add default headers
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    // Add auth token if available
    const token = this.getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMsg = response.statusText;
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errorMsg;
      } catch (e) {
        // Ignore JSON parse error
      }
      throw new Error(errorMsg);
    }

    // Return blob for PDF
    if (response.headers.get("Content-Type")?.includes("application/pdf")) {
      return response.blob();
    }
    
    // Return text for Markdown
    if (response.headers.get("Content-Type")?.includes("text/markdown")) {
      return response.text();
    }

    return response.json();
  }

  async get(endpoint: string) {
    return this.request(endpoint, { method: "GET" });
  }

  async post(endpoint: string, data: any) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Helper for SSE streaming
  createEventSource(endpoint: string) {
    const token = this.getToken();
    // Use URL params for auth if SSE doesn't support custom headers in browser EventSource
    // Actually, EventSource doesn't support headers.
    // Better to use fetch API with a custom reader for SSE to pass headers.
    return fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST", // SSE via POST
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
    });
  }
}

export const api = new ApiClient();
