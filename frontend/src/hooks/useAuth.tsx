import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase, isSupabaseConfigured } from '../lib/supabase';

export interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isConfigured: boolean;
  loginWithGoogle: () => Promise<{ error?: string }>;
  login: (email: string, password: string) => Promise<{ error?: string }>;
  signup: (name: string, email: string, password: string) => Promise<{ error?: string }>;
  resetPassword: (email: string) => Promise<{ error?: string; success?: boolean }>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function mapSupabaseUser(sbUser: any): User {
  const name =
    sbUser.user_metadata?.full_name ||
    sbUser.user_metadata?.name ||
    sbUser.email?.split('@')[0] ||
    'Researcher';

  const avatarUrl =
    sbUser.user_metadata?.avatar_url ||
    sbUser.user_metadata?.picture ||
    undefined;

  return {
    id: sbUser.id,
    name,
    email: sbUser.email || '',
    avatarUrl,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('quorum_mock_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setIsLoading(false);
      return;
    }

    // 1. Get initial session on app mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser(mapSupabaseUser(session.user));
      }
      setIsLoading(false);
    });

    // 2. Listen to real-time auth changes (sign in, sign out, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser(mapSupabaseUser(session.user));
      } else {
        setUser(null);
        localStorage.removeItem('quorum_mock_user');
      }
      setIsLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // Sync mock user fallback to local storage
  useEffect(() => {
    if (!isSupabaseConfigured) {
      if (user) {
        localStorage.setItem('quorum_mock_user', JSON.stringify(user));
      } else {
        localStorage.removeItem('quorum_mock_user');
      }
    }
  }, [user]);

  const loginWithGoogle = async (): Promise<{ error?: string }> => {
    setIsLoading(true);

    if (isSupabaseConfigured) {
      try {
        const { error } = await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: {
            redirectTo: window.location.origin,
          },
        });
        setIsLoading(false);
        if (error) {
          console.warn('Google OAuth error:', error);
          return {
            error:
              'Google login is not enabled yet in your Supabase project. Please create an account or sign in with your email & password below, or enable the Google provider in your Supabase Dashboard.',
          };
        }
        return {};
      } catch (err: any) {
        setIsLoading(false);
        return { error: err.message || 'Google sign-in failed' };
      }
    }

    fallbackMockLogin();
    setIsLoading(false);
    return {};
  };

  const fallbackMockLogin = () => {
    const googleUser: User = {
      id: 'usr_google_123',
      name: 'Alex Rivera',
      email: 'alex.rivera@gmail.com',
      avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop&crop=faces',
    };
    setUser(googleUser);
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);

    if (isSupabaseConfigured) {
      try {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        setIsLoading(false);
        if (error) {
          return { error: error.message };
        }

        if (data.user) {
          setUser(mapSupabaseUser(data.user));
        }
        return {};
      } catch (err: any) {
        setIsLoading(false);
        return { error: err.message || 'Login failed' };
      }
    }

    // Fallback simulation
    await new Promise((r) => setTimeout(r, 400));
    setIsLoading(false);

    if (password.length < 6) {
      return { error: 'Password must be at least 6 characters long.' };
    }

    const newUser: User = {
      id: 'usr_' + Date.now(),
      name: email.split('@')[0],
      email: email,
    };
    setUser(newUser);
    return {};
  };

  const signup = async (name: string, email: string, password: string) => {
    setIsLoading(true);

    if (isSupabaseConfigured) {
      try {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: name,
              name: name,
            },
          },
        });

        setIsLoading(false);
        if (error) {
          return { error: error.message };
        }

        if (data.user) {
          setUser(mapSupabaseUser(data.user));
        }
        return {};
      } catch (err: any) {
        setIsLoading(false);
        return { error: err.message || 'Signup failed' };
      }
    }

    // Fallback simulation
    await new Promise((r) => setTimeout(r, 400));
    setIsLoading(false);

    if (password.length < 8) {
      return { error: 'Please choose a stronger password with at least 8 characters.' };
    }

    const newUser: User = {
      id: 'usr_' + Date.now(),
      name: name || email.split('@')[0],
      email: email,
    };
    setUser(newUser);
    return {};
  };

  const resetPassword = async (email: string) => {
    setIsLoading(true);

    if (isSupabaseConfigured) {
      try {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: window.location.origin,
        });
        setIsLoading(false);
        if (error) {
          return { error: error.message };
        }
        return { success: true };
      } catch (err: any) {
        setIsLoading(false);
        return { error: err.message };
      }
    }

    await new Promise((r) => setTimeout(r, 400));
    setIsLoading(false);
    return { success: true };
  };

  const logout = async () => {
    if (isSupabaseConfigured) {
      try {
        await supabase.auth.signOut();
      } catch (err) {
        console.warn('Error signing out:', err);
      }
    }
    setUser(null);
    localStorage.removeItem('quorum_mock_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isConfigured: isSupabaseConfigured,
        loginWithGoogle,
        login,
        signup,
        resetPassword,
        logout,
      }}
    >
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
