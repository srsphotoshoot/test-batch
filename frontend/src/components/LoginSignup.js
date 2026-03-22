import React, { useState } from 'react';
import './LoginSignup.css';

// Use proxy configured in package.json, or fallback to localhost
import API_BASE_URL from '../api_config';

function LoginSignup({ onLoginSuccess }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [passkey, setPasskey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (!email || !password) {
      setError('Please enter email and password');
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Login failed');
        setLoading(false);
        return;
      }

      // Save token and user data to sessionStorage (Transient)
      sessionStorage.setItem('token', data.access_token);
      sessionStorage.setItem('user', JSON.stringify({
        id: data.user_id,
        email: data.email,
        role: data.role
      }));

      onLoginSuccess(data);
    } catch (err) {
      setError('Login error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (!email || !password || !passkey || !firstName || !lastName) {
      setError('Please fill in all fields (Email, Password, Names, and Passkey)');
      setLoading(false);
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email, 
          password, 
          passkey,
          first_name: firstName,
          last_name: lastName
        })
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Signup failed');
        setLoading(false);
        return;
      }

      setError('');
      alert('Signup successful! Please login.');
      setIsSignup(false);
      setEmail('');
      setPassword('');
      setFirstName('');
      setLastName('');
      setPasskey('');
    } catch (err) {
      setError('Signup error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-signup-container">
      <div className="login-signup-box">
        <div className="login-logo">
          <img src="/2.png" alt="SRS Logo" />
        </div>
        <h2>{isSignup ? '📝 Sign Up' : '🔐 Shree Radha Studio (SRS)'}</h2>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={isSignup ? handleSignup : handleLogin}>
          {isSignup && (
            <div className="form-row">
              <div className="form-group half-width">
                <label htmlFor="firstName">First Name:</label>
                <input
                  id="firstName"
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="First Name"
                  disabled={loading}
                />
              </div>
              <div className="form-group half-width">
                <label htmlFor="lastName">Last Name:</label>
                <input
                  id="lastName"
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Last Name"
                  disabled={loading}
                />
              </div>
            </div>
          )}
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password:</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              disabled={loading}
            />
          </div>

          {isSignup && (
            <div className="form-group">
              <label htmlFor="passkey">Signup Passkey:</label>
              <input
                id="passkey"
                type="password"
                value={passkey}
                onChange={(e) => setPasskey(e.target.value)}
                placeholder="Enter signup passkey (from backend team)"
                disabled={loading}
              />
              <small>⚠️ Contact backend team for the passkey</small>
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-submit">
            {loading ? '⏳ Processing...' : (isSignup ? 'Sign Up' : 'Login')}
          </button>
        </form>

        <div className="toggle-form">
          <p>
            {isSignup ? 'Already have an account? ' : "Don't have an account? "}
            <button
              type="button"
              onClick={() => {
                setIsSignup(!isSignup);
                setError('');
                setEmail('');
                setPassword('');
                setFirstName('');
                setLastName('');
                setPasskey('');
              }}
              className="link-button"
            >
              {isSignup ? 'Login' : 'Sign Up'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginSignup;
