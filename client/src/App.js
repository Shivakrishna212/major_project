import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';

// Contexts
import { AuthProvider, useAuth } from './context/AuthContext';
import { HistoryProvider } from './context/HistoryContext';

// Components
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import Roadmap from './components/Roadmap';
import Sidebar from './components/Sidebar';
import Profile from './components/Profile'; // ✅ IMPORT ADDED HERE

import './App.css';

// --- LAYOUT COMPONENT ---
const Layout = () => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Outlet />
      </div>
    </div>
  );
};

// --- MAIN APP COMPONENT ---
function App() {
  return (
    <AuthProvider>
      <HistoryProvider>
        <Router>
          <div className="App">
            <Routes>
              
              {/* PUBLIC ROUTE: Login */}
              <Route path="/" element={<PublicOnlyRoute />} />

              {/* PROTECTED ROUTES (With Sidebar) */}
              <Route element={<Layout />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/roadmap" element={<Roadmap />} />
                <Route path="/profile" element={<Profile />} /> 
              </Route>

              {/* CATCH-ALL */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />

            </Routes>
          </div>
        </Router>
      </HistoryProvider>
    </AuthProvider>
  );
}

// Helper: Redirects logged-in users away from Login page
const PublicOnlyRoute = () => {
  const { user } = useAuth();
  return user ? <Navigate to="/dashboard" replace /> : <Login />;
};

export default App;