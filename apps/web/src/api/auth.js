import { apiFetch, clearStoredToken, getStoredToken, setStoredToken } from "./client.js";

export { getStoredToken };

/**
 * Logs in an existing user and stores bearer JWT.
 * @param {{ email: string, password: string }} credentials
 * @returns {Promise<{ access_token: string, user: any }>}
 */
export async function login({ email, password }) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

/**
 * Registers a new organization and initial administrator user.
 * @param {{ org_name: string, org_slug: string, full_name: string, email: string, password: string }} payload
 * @returns {Promise<{ access_token: string, user: any }>}
 */
export async function register(payload) {
  const data = await apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

/**
 * Retrieves current authenticated user profile and organization details.
 * @returns {Promise<{ user: any, organization: any }>}
 */
export async function getMe() {
  return apiFetch("/auth/me");
}

/**
 * Clears stored JWT token and logs out user.
 */
export function logout() {
  clearStoredToken();
}

