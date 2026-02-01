import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import '../App.css';

const Profile = () => {
  const { user, login, logout } = useAuth(); // 'login' helps update local user context
  const navigate = useNavigate();

  const [stats, setStats] = useState({
    topics_started: 0,
    modules_completed: 0,
    total_xp: 0,
    level: 1
  });

  const [isEditing, setIsEditing] = useState(false);
  const [newName, setNewName] = useState(user?.name || "");
  const [loading, setLoading] = useState(false);

  // ✅ FIX: Moved fetchStats INSIDE useEffect
  useEffect(() => {
    const fetchStats = async () => {
      try {
          const res = await fetch('http://127.0.0.1:5000/api/get_user_stats', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: user.id })
          });
          const data = await res.json();
          if (!data.error) setStats(data);
      } catch (err) {
          console.error("Stats fetch error:", err);
      }
    };

    if (user) {
        fetchStats();
        setNewName(user.name);
    }
  }, [user]); // Now this is safe and correct

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
        const res = await fetch('http://127.0.0.1:5000/api/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, name: newName })
        });
        
        if (res.ok) {
            // Update local context so the Sidebar/Header updates instantly
            const updatedUser = { ...user, name: newName };
            login(updatedUser); 
            setIsEditing(false);
            alert("Profile updated successfully!");
        }
    } catch (err) {
        alert("Failed to update profile.");
    } finally {
        setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (!user) return <div className="main-content-centered">Loading...</div>;

  return (
    <div className="container" style={{ padding: '40px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '30px' }}>Account Settings</h1>

      <div className="profile-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '30px' }}>
        
        {/* LEFT COLUMN: Identity Card */}
        <div className="lesson-card-large" style={{ textAlign: 'center', height: 'fit-content' }}>
            <div style={{ 
                width: '100px', height: '100px', borderRadius: '50%', 
                background: 'linear-gradient(135deg, #4285f4 0%, #34a853 100%)', 
                color: 'white', fontSize: '2.5rem', fontWeight: 'bold',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 20px auto', boxShadow: '0 4px 10px rgba(0,0,0,0.1)'
            }}>
                {user.name.charAt(0).toUpperCase()}
            </div>
            <h2>{user.name}</h2>
            <p style={{ color: '#666' }}>{user.email}</p>
            <div className="badge" style={{ 
                display: 'inline-block', padding: '5px 15px', 
                background: '#e8f0fe', color: '#1a73e8', borderRadius: '15px',
                marginTop: '10px', fontWeight: '600'
            }}>
                Level {stats.level} Scholar
            </div>
        </div>

        {/* RIGHT COLUMN: Stats & Edit Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* 1. STATS ROW */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
                <div className="stat-card" style={statCardStyle}>
                    <h3>🔥 {stats.total_xp}</h3>
                    <span>Total XP</span>
                </div>
                <div className="stat-card" style={statCardStyle}>
                    <h3>📚 {stats.topics_started}</h3>
                    <span>Topics Started</span>
                </div>
                <div className="stat-card" style={statCardStyle}>
                    <h3>✅ {stats.modules_completed}</h3>
                    <span>Modules Done</span>
                </div>
            </div>

            {/* 2. EDIT DETAILS FORM */}
            <div className="lesson-card-large">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h3 style={{ margin: 0 }}>Personal Details</h3>
                    {!isEditing && (
                        <button className="secondary-btn" onClick={() => setIsEditing(true)}>✎ Edit</button>
                    )}
                </div>

                <form onSubmit={handleUpdateProfile}>
                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', color: '#555', fontSize: '0.9rem' }}>Full Name</label>
                        <input 
                            type="text" 
                            value={newName} 
                            onChange={(e) => setNewName(e.target.value)}
                            disabled={!isEditing}
                            style={{ 
                                width: '100%', padding: '12px', borderRadius: '8px', 
                                border: '1px solid #ddd', background: isEditing ? '#fff' : '#f9f9f9',
                                color: isEditing ? '#000' : '#666'
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', color: '#555', fontSize: '0.9rem' }}>Email Address</label>
                        <input 
                            type="text" 
                            value={user.email} 
                            disabled 
                            style={{ 
                                width: '100%', padding: '12px', borderRadius: '8px', 
                                border: '1px solid #ddd', background: '#f9f9f9', color: '#888',
                                cursor: 'not-allowed'
                            }}
                        />
                        <small style={{ color: '#999' }}>Email cannot be changed.</small>
                    </div>

                    {isEditing && (
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button type="submit" className="primary-btn" disabled={loading}>
                                {loading ? "Saving..." : "Save Changes"}
                            </button>
                            <button type="button" className="secondary-btn" onClick={() => setIsEditing(false)}>
                                Cancel
                            </button>
                        </div>
                    )}
                </form>
            </div>

            {/* 3. DANGER ZONE */}
            <div className="lesson-card-large" style={{ border: '1px solid #ffebee' }}>
                <h3 style={{ margin: '0 0 15px 0', color: '#d93025' }}>Sign Out</h3>
                <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '15px' }}>
                    Securely log out of your account on this device.
                </p>
                <button 
                    onClick={handleLogout} 
                    style={{ 
                        background: '#fff', border: '1px solid #d93025', color: '#d93025',
                        padding: '10px 20px', borderRadius: '6px', cursor: 'pointer', fontWeight: '600'
                    }}
                >
                    Log Out
                </button>
            </div>

        </div>
      </div>
    </div>
  );
};

// Simple inline style for the stat boxes
const statCardStyle = {
    background: 'white',
    padding: '20px',
    borderRadius: '12px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
    textAlign: 'center',
    border: '1px solid #eee'
};

export default Profile;