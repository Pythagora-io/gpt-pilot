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
    return !!localStorage.getItem("token");
  });

  const login = async (email: string, password: string) => {
    const response = await apiLogin(email, password);
    console.log('....', response);
    if (response.success) {
      localStorage.setItem("token", response.token);
      setIsAuthenticated(true);
    } else {
      throw new Error(response.message);
    }
  };

  const register = async (email: string, password: string) => {
    const response = await apiRegister(email, password);
    if (response.success) {
      localStorage.setItem("token", response.token);
      setIsAuthenticated(true);
    } else {
      throw new Error(response.message);
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