/**
 * Centralized API client wrapper with JWT header injection, response parsing, and 401 handling.
 */

const TOKEN_KEY = "cite_access_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Base fetch wrapper with auth header and error extraction.
 * @param {string} path - URL path relative to API root (e.g. '/documents')
 * @param {RequestInit} [options={}] - Standard fetch options
 * @returns {Promise<any>}
 */
export async function apiFetch(path, options = {}) {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  // Add auth header if token exists
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Set default JSON Content-Type if not sending FormData
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `/api${normalizedPath}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle unauthorized / token expired
  if (response.status === 401) {
    clearStoredToken();
    if (window.location.pathname !== "/login" && window.location.pathname !== "/register") {
      window.location.href = "/login?expired=1";
    }
    throw new Error("Authentication session expired. Please log in again.");
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  // Parse error response
  if (!response.ok) {
    let errorMessage = `API request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      errorMessage = errorJson.detail || errorJson.message || errorMessage;
    } catch (e) {
      // Body not JSON
    }
    const err = new Error(errorMessage);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

