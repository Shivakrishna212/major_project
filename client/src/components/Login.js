import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../App.css'; // Ensure you have basic styles

const Login = () => {
  const [isLogin, setIsLogin] = useState(true); // Toggle between Login and Signup
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    const endpoint = isLogin ? '/api/login' : '/api/signup';
    const body = isLogin ? { email, password } : { email, password, name };

    try {
      const res = await fetch(`http://127.0.0.1:5000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Something went wrong');
      }

      if (isLogin) {
        login(data.user); // Save user to context
        navigate('/dashboard'); // Go to main app
      } else {
        // After signup, switch to login view or auto-login
        setIsLogin(true);
        setError('Account created! Please log in.');
      }

    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="container" style={{maxWidth: '400px', marginTop: '100px'}}>
      <div className="lesson-card-large" style={{textAlign: 'center'}}>
        <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
        {error && <p style={{color: 'red'}}>{error}</p>}
        
        <form onSubmit={handleSubmit} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
          {!isLogin && (
            <input 
              type="text" 
              placeholder="Full Name" 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
              required
              style={{padding: '10px', borderRadius: '5px', border: '1px solid #ddd'}}
            />
          )}
          <input 
            type="email" 
            placeholder="Email Address" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            required
            style={{padding: '10px', borderRadius: '5px', border: '1px solid #ddd'}}
          />
          <input 
            type="password" 
            placeholder="Password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            required
            style={{padding: '10px', borderRadius: '5px', border: '1px solid #ddd'}}
          />
          
          <button type="submit" className="primary-btn">
            {isLogin ? 'Login' : 'Sign Up'}
          </button>
        </form>

        <p style={{marginTop: '20px', fontSize: '0.9rem'}}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <span 
            onClick={() => setIsLogin(!isLogin)} 
            style={{color: '#4285f4', cursor: 'pointer', fontWeight: 'bold'}}
          >
            {isLogin ? 'Sign Up' : 'Login'}
          </span>
        </p>
      </div>
    </div>
  );
};

export default Login;