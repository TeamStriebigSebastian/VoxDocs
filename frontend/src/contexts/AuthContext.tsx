
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';

interface UserRole {
    group_id: number;
    role: 'admin' | 'superuser' | 'user' | 'viewer';
    can_manage_users: boolean;
}

interface User {
    id: number;
    uuid: string;
    username: string;
    email: string;
    tenant_id: number;
    active: boolean;
    roles: UserRole[];
}

interface AuthContextType {
    user: User | null;
    accessToken: string | null;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
    isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [accessToken, setAccessToken] = useState<string | null>(localStorage.getItem('access_token'));
    const [isLoading, setIsLoading] = useState(true);

    // Initialize auth state
    useEffect(() => {
        const initAuth = async () => {
            const token = localStorage.getItem('access_token');
            if (token) {
                try {
                    // Sync with AppStore immediately so API calls work
                    useAppStore.getState().setToken(token);
                    await fetchUser(token);
                } catch (error) {
                    console.error('Auth initialization failed:', error);
                    logout();
                }
            }
            setIsLoading(false);
        };

        initAuth();
    }, []);

    const fetchUser = async (token: string) => {
        try {
            const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                const userData = await res.json();
                setUser(userData);
                setAccessToken(token); // Update state if needed

                // Sync User Info to AppStore
                const primaryRole = userData.roles.length > 0 ? userData.roles[0].role : 'viewer';
                useAppStore.getState().setUserInfo(
                    userData.id,
                    userData.username, // Using username as name for now
                    primaryRole,
                    'de' // Default language
                );
            } else {
                throw new Error('Failed to fetch user');
            }
        } catch (error) {
            throw error;
        }
    };

    const login = async (username: string, password: string) => {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Login failed');
        }

        const data = await res.json();
        const token = data.access_token;

        // Store tokens
        localStorage.setItem('access_token', token);
        localStorage.setItem('refresh_token', data.refresh_token);
        setAccessToken(token);

        // Sync with AppStore (for API interceptors)
        useAppStore.getState().setToken(token);

        // Fetch user details
        await fetchUser(token);
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setAccessToken(null);
        setUser(null);

        // Sync with AppStore
        useAppStore.getState().logout();

        // Optional: Call server logout endpoint
        fetch('/api/auth/logout', { method: 'POST' }).catch(console.error);
    };

    return (
        <AuthContext.Provider value={{
            user,
            accessToken,
            isLoading,
            login,
            logout,
            isAuthenticated: !!user
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
