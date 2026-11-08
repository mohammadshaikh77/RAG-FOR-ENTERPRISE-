
/**
 * Centralized API client wrapper.
 *
 * Features:
 * - Production and local API URL support
 * - JWT authorization header injection
 * - JSON request/response handling
 * - FormData upload support
 * - 401 authentication handling
 * - API error extraction
 */

const TOKEN_KEY = "cite_access_token";

// --------------------------------------------------
// Authentication helpers
// --------------------------------------------------

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// --------------------------------------------------
// API configuration
// --------------------------------------------------

const API_BASE_URL = (
  import.meta.env.VITE_API_URL || ""
).replace(/\/+$/, "");

/**
 * Base fetch wrapper with authentication and error handling.
 *
 * @param {string} path - API path, e.g. "/auth/register"
 * @param {RequestInit} [options={}] - Fetch options
 * @returns {Promise<any>}
 */
export async function apiFetch(path, options = {}) {
  // Normalize API path
  const normalizedPath = path.startsWith("/")
    ? path
    : `/${path}`;

  // Build API URL
  // Production: https://your-render-api.com/auth/register
  // Development: /api/auth/register (Vite proxy)
  const url = API_BASE_URL
    ? `${API_BASE_URL}${normalizedPath}`
    : `/api${normalizedPath}`;

  // Prepare request headers
  const headers = new Headers(options.headers || {});

  // Add JWT if available
  const token = getStoredToken();

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Set JSON Content-Type only when a body exists.
  // Do not set it for GET requests or FormData uploads.
  const isFormData =
    typeof FormData !== "undefined" &&
    options.body instanceof FormData;

  if (
    options.body != null &&
    !isFormData &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  // Make API request
  const response = await fetch(url, {
    ...options,
    headers,
  });

  // --------------------------------------------------
  // Handle unauthorized / expired JWT
  // --------------------------------------------------

  if (response.status === 401) {
    clearStoredToken();

    if (
      window.location.pathname !== "/login" &&
      window.location.pathname !== "/register"
    ) {
      window.location.href = "/login?expired=1";
    }

    throw new Error(
      "Authentication session expired. Please log in again."
    );
  }

  // --------------------------------------------------
  // Handle empty responses
  // --------------------------------------------------

  if (
    response.status === 204 ||
    response.status === 205
  ) {
    return null;
  }

  // --------------------------------------------------
  // Handle API errors
  // --------------------------------------------------

  if (!response.ok) {
    let errorMessage =
      `API request failed with status ${response.status}`;

    try {
      const errorJson = await response.json();

      errorMessage =
        errorJson.detail ||
        errorJson.message ||
        errorMessage;
    } catch {
      // Response was not valid JSON.
    }

    const error = new Error(errorMessage);
    error.status = response.status;

    throw error;
  }

  // --------------------------------------------------
  // Parse successful response
  // --------------------------------------------------

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
