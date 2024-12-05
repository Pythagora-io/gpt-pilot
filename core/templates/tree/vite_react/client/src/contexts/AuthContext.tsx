{% raw %}
import { createContext, useContext, useState, ReactNode } from "react";
import { login as apiLogin, register as apiRegister } from "@/api/auth";

type AuthContextType = {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return true; // this is just a placeholder - remove when the backend is being implemented
    return !!localStorage.getItem("token");
  });

  const login = async (email: string, password: string) => {
    try {
      return await setTimeout(() => {setIsAuthenticated(true)}, 1000); // this is just a placeholder - remove when the backend is being implemented
      const response = await apiLogin(email, password);
      if (response.data?.token) {
        localStorage.setItem("token", response.data.token);
        setIsAuthenticated(true);
      } else {
        throw new Error(response.data.error || "Login failed");
      }
    } catch (error) {
      localStorage.removeItem("token");
      setIsAuthenticated(false);
      throw error;
    }
  };

  const register = async (email: string, password: string) => {
    try {
      return await setTimeout(() => {setIsAuthenticated(true)}, 1000); // this is just a placeholder - remove when the backend is being implemented
      const response = await apiRegister(email, password);
      if (response.data?.token) {
        localStorage.setItem("token", response.data.token);
        setIsAuthenticated(true);
      } else {
        throw new Error(response.data.error || "Registration failed");
      }
    } catch (error) {
      localStorage.removeItem("token");
      setIsAuthenticated(false);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
{% endraw %}
