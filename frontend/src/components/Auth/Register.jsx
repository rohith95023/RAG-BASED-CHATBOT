/**
 * Register Component
 * Provides user registration interface with form validation
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

const Register = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [passwordRequirements, setPasswordRequirements] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });

  const validatePassword = (password) => {
    setPasswordRequirements({
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Validate password if that's the field being changed
    if (name === 'password') {
      validatePassword(value);
    }

    setError(''); // Clear error on input change
  };

  const isFormValid = () => {
    return (
      formData.username.trim() &&
      formData.email.trim() &&
      formData.password &&
      formData.confirmPassword &&
      formData.password === formData.confirmPassword &&
      Object.values(passwordRequirements).every(Boolean)
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    if (!formData.username.trim()) {
      setError('Please enter a username');
      return;
    }

    if (formData.username.length < 3 || formData.username.length > 20) {
      setError('Username must be 3-20 characters long');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return;
    }

    if (!isFormValid()) {
      setError('Please fill in all fields correctly');
      return;
    }

    setLoading(true);

    try {
      const result = await register(
        formData.username,
        formData.email,
        formData.password,
        formData.confirmPassword
      );

      if (result.success) {
        // Navigate to dashboard after successful registration
        navigate('/dashboard', { replace: true });
      } else {
        setError(result.error || 'Registration failed');
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>Create Account</h1>
          <p>Join FLASH MAN and start chatting with your documents</p>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Choose a username (3-20 characters)"
              disabled={loading}
              required
              autoComplete="username"
              minLength={3}
              maxLength={20}
            />
            <small className="form-hint">3-20 characters</small>
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email"
              disabled={loading}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Create a strong password"
              disabled={loading}
              required
              autoComplete="new-password"
            />
            <div className="password-requirements">
              <div className={`requirement ${passwordRequirements.length ? 'met' : 'unmet'}`}>
                ✓ At least 8 characters
              </div>
              <div className={`requirement ${passwordRequirements.uppercase ? 'met' : 'unmet'}`}>
                ✓ Uppercase letter
              </div>
              <div className={`requirement ${passwordRequirements.lowercase ? 'met' : 'unmet'}`}>
                ✓ Lowercase letter
              </div>
              <div className={`requirement ${passwordRequirements.number ? 'met' : 'unmet'}`}>
                ✓ Number
              </div>
              <div className={`requirement ${passwordRequirements.special ? 'met' : 'unmet'}`}>
                ✓ Special character
              </div>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm your password"
              disabled={loading}
              required
              autoComplete="new-password"
            />
            {formData.confirmPassword && formData.password !== formData.confirmPassword && (
              <small className="error-hint">Passwords do not match</small>
            )}
          </div>

          <button
            type="submit"
            className="auth-button"
            disabled={loading || !isFormValid()}
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <div className="auth-footer">
          <p>Already have an account? <a href="/login">Sign in</a></p>
        </div>
      </div>
    </div>
  );
};

export default Register;
