/**
 * Authentication Context for global auth state management
 * Provides user authentication state and methods across the app
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const userData = await authAPI.getCurrentUser();
          setUser(userData);
          setIsAuthenticated(true);
        } catch (error) {
          // Invalid token, clear it
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          setIsAuthenticated(false);
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (username, password) => {
    try {
      const data = await authAPI.login(username, password);

      // Store tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      // Set user data (we'll fetch it)
      const userData = await authAPI.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Login failed'
      };
    }
  };

  const register = async (username, email, password, confirmPassword) => {
    try {
      const userData = await authAPI.register(username, email, password, confirmPassword);

      // Automatically login after registration
      const loginResult = await login(username, password);

      return { success: true, user: userData };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Registration failed'
      };
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');

      // Clear auth state
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const updateProfile = async (profileData) => {
    try {
      const updatedUser = await authAPI.updateProfile(profileData);
      setUser(updatedUser);
      return { success: true, user: updatedUser };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Profile update failed'
      };
    }
  };

  const changePassword = async (currentPassword, newPassword, confirmPassword) => {
    try {
      await authAPI.changePassword(currentPassword, newPassword, confirmPassword);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Password change failed'
      };
    }
  };

  const refreshToken = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const data = await authAPI.refreshToken(refreshToken);

      // Update access token
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      return { success: true };
    } catch (error) {
      // Refresh failed, logout user
      await logout();
      return {
        success: false,
        error: error.message || 'Token refresh failed'
      };
    }
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};