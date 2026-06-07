"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { api } from "./api";
import { useRouter, usePathname } from "next/navigation";

interface User {
  username: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("dsmi_token");
      if (token) {
        try {
          const userData = await api.get("/auth/me");
          setUser(userData);
        } catch (error) {
          localStorage.removeItem("dsmi_token");
          setUser(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  useEffect(() => {
    // Redirect logic
    if (!loading) {
      if (!user && pathname !== "/" && pathname !== "/login") {
        router.push("/login");
      } else if (user && (pathname === "/" || pathname === "/login")) {
        router.push("/dashboard");
      }
    }
  }, [user, loading, pathname, router]);

  const login = (token: string, userData: User) => {
    localStorage.setItem("dsmi_token", token);
    setUser(userData);
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("dsmi_token");
    setUser(null);
    router.push("/");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
