import React, { createContext, useContext, useEffect, useState } from "react";
import { getMe, getStoredToken, login, logout, register } from "../api/auth.js";

const AuthContext = createContext({
  user: null,
  organization: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshProfile: async () => {},
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshProfile = async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setOrganization(null);
      setIsLoading(false);
      return;
    }
    try {
      const data = await getMe();
      const currentUser = data?.user || data;
      const currentOrg =
        data?.organization ||
        currentUser?.organization || {
          id: currentUser?.org_id,
          name: "Tenant Workspace",
        };
      setUser(currentUser);
      setOrganization(currentOrg);
    } catch (err) {
      setUser(null);
      setOrganization(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshProfile();
  }, []);

  const handleLogin = async (credentials) => {
    setIsLoading(true);
    try {
      const res = await login(credentials);
      await refreshProfile();
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (payload) => {
    setIsLoading(true);
    try {
      const res = await register(payload);
      await refreshProfile();
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    setUser(null);
    setOrganization(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        organization,
        isAuthenticated: !!user,
        isLoading,
        login: handleLogin,
        register: handleRegister,
        logout: handleLogout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

