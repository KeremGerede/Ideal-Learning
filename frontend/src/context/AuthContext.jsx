// src/context/AuthContext.jsx

import { createContext, useContext, useState, useCallback } from "react";
import { loginUser, registerUser, getMe } from "../api/apiClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(() => localStorage.getItem("auth_token"));
    const [user, setUser] = useState(() => {
        const stored = localStorage.getItem("auth_user");
        try {
            return stored ? JSON.parse(stored) : null;
        } catch {
            return null;
        }
    });

    const login = useCallback(async (username, password) => {
        const data = await loginUser({ username, password });
        localStorage.setItem("auth_token", data.access_token);
        setToken(data.access_token);

        const me = await getMe(data.access_token);
        localStorage.setItem("auth_user", JSON.stringify(me));
        setUser(me);
    }, []);

    const register = useCallback(async (username, email, password) => {
        await registerUser({ username, email, password });
        await login(username, password);
    }, [login]);

    const logout = useCallback(() => {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        setToken(null);
        setUser(null);
    }, []);

    const isAuthenticated = !!token;

    return (
        <AuthContext.Provider value={{ token, user, isAuthenticated, login, register, logout }}>
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
