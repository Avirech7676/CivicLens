'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { loginUser, getAuthMe, setAuthToken, clearAuthToken, getAuthToken } from '@/lib/api';
import { UserRole } from '@/types';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department?: string | null;
}

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  logout: () => void;
  isAuthenticated: boolean;
  isCitizen: boolean;
  isDispatcher: boolean;
  isFieldCrew: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Restore cached user after initial hydration pass to ensure 100% identical SSR/client initial markup
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('civiclens_user');
        if (saved) {
          setUser(JSON.parse(saved));
        }
      } catch {
        // ignore parse error
      }
    }

    // 2. Validate token and update user profile in background
    const token = getAuthToken();
    if (token) {
      getAuthMe()
        .then((userData) => {
          setUser(userData);
          if (typeof window !== 'undefined') {
            localStorage.setItem('civiclens_user', JSON.stringify(userData));
          }
        })
        .catch(() => {
          clearAuthToken();
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string): Promise<UserProfile> => {
    const data = await loginUser(email, password);
    setAuthToken(data.access_token);
    const userProfile: UserProfile = {
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      role: data.role,
      department: data.department
    };
    setUser(userProfile);
    if (typeof window !== 'undefined') {
      localStorage.setItem('civiclens_user', JSON.stringify(userProfile));
    }
    return userProfile;
  };

  const logout = () => {
    clearAuthToken();
    setUser(null);
  };

  const isAuthenticated = Boolean(user);
  const isCitizen = user?.role === 'CITIZEN';
  const isDispatcher = user?.role === 'DISPATCHER';
  const isFieldCrew = user?.role === 'FIELD_CREW';

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated, isCitizen, isDispatcher, isFieldCrew }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
