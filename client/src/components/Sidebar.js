import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { createPortal } from 'react-dom'; // ✅ Import Portal for popup fix
import '../App.css';

const Sidebar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  // State
  const [history, setHistory] = useState([]);
  const [xp, setXp] = useState(user?.xp || 0);
  const [level, setLevel] = useState(user?.level || 1);
  const [riskData, setRiskData] = useState({ score: 0, level: 'Low' });
  const [streak, setStreak] = useState(0);
  const [showRescueModal, setShowRescueModal] = useState(false);

  // Notifications
  const [showNotif, setShowNotif] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // 1. Fetch Data
  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;
      try {
          // A. History
          const resHist = await fetch('http://127.0.0.1:5000/api/get_user_history', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: user.id })
          });
          const dataHist = await resHist.json();
          setHistory(dataHist.history || []);

          // B. Risk
          const resRisk = await fetch('http://127.0.0.1:5000/api/predict_dropout_risk', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: user.id })
          });
          const dataRisk = await resRisk.json();
          if (dataRisk.risk_level) setRiskData({ score: dataRisk.risk_score, level: dataRisk.risk_level });

          // C. Streak
          const resStreak = await fetch('http://127.0.0.1:5000/api/update_streak', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: user.id })
          });
          const dataStreak = await resStreak.json();
          setStreak(dataStreak.streak);

          // D. Notifications
          const resNotif = await fetch('http://127.0.0.1:5000/api/get_notifications', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: user.id })
          });
          const dataNotif = await resNotif.json();
          setNotifications(dataNotif.notifications || []);
          setUnreadCount(dataNotif.notifications?.length || 0);

      } catch (err) { console.error(err); }
    };

    fetchData();
    if (user) { setXp(user.xp); setLevel(user.level); }
  }, [user, location.pathname]);

  // 2. XP Listener
  useEffect(() => {
    const handleXpUpdate = (e) => { setXp(e.detail.xp); setLevel(e.detail.level); };
    window.addEventListener('xp-update', handleXpUpdate);
    return () => window.removeEventListener('xp-update', handleXpUpdate);
  }, []);

  // Handlers
  const handleNewChat = () => navigate('/dashboard');
  
  const handleHistoryClick = (attemptId, topic) => {
      navigate('/roadmap', { state: { attemptId, definition: { topic, definition: "Loading..." } } });
  };
  
  const handleDeleteTopic = async (e, attemptId) => {
    e.stopPropagation();
    if (!window.confirm("Delete this topic?")) return;
    setHistory(prev => prev.filter(item => item.id !== attemptId));
    try {
        await fetch('http://127.0.0.1:5000/api/delete_topic', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ attempt_id: attemptId })
        });
        if (location.state?.attemptId === attemptId) navigate('/dashboard');
    } catch (err) { console.error(err); }
  };

  const handleLogout = () => { logout(); navigate('/'); };
  const xpProgress = ((xp % 100) / 100) * 100;
  
  const getRiskColor = () => {
      if (riskData.level === 'High') return '#ff6b6b'; 
      if (riskData.level === 'Medium') return '#ff9800'; 
      return '#4caf50'; 
  };

  const handleAcceptRescue = () => {
      setShowRescueModal(false);
      setRiskData({ score: 12, level: 'Low' });
      alert("✅ Success! Refresher Module Added.");
  };

  const toggleNotif = () => {
      setShowNotif(!showNotif);
      if (!showNotif) setUnreadCount(0);
  };

  return (
    <div className="sidebar" style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      
      {/* RESCUE MODAL */}
      {showRescueModal && (
          <div className="modal-overlay fade-in" style={{zIndex: 2000}}>
              <div className="modal-content" style={{maxWidth: '400px', textAlign: 'center'}}>
                  <h2 style={{color: '#ff6b6b'}}>⚠️ Risk Alert</h2>
                  <p>Risk Score: <strong>{riskData.score}%</strong></p>
                  <p>We've prepared a refresher module for you.</p>
                  <button className="primary-btn" onClick={handleAcceptRescue}>🚀 Accept</button>
              </div>
          </div>
      )}

      {/* HEADER & NOTIFICATIONS */}
      <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, paddingBottom:'20px' }}>
        <h2 style={{margin:0, fontSize:'1.4rem'}}>🚀 LearnAI</h2>
        
        <div style={{ position: 'relative', cursor: 'pointer' }} onClick={toggleNotif}>
            <span style={{ fontSize: '1.2rem' }}>🔔</span>
            {unreadCount > 0 && (
                <div style={{ position: 'absolute', top: -5, right: -5, background: 'red', color: 'white', fontSize: '0.6rem', padding: '2px 5px', borderRadius: '50%' }}>
                    {unreadCount}
                </div>
            )}
            
            {/* ✅ PORTAL FIX: Renders outside sidebar to avoid clipping */}
            {showNotif && createPortal(
                <div className="notification-dropdown" style={{ 
                    position: 'fixed', 
                    top: '60px', 
                    left: '270px', /* Adjust based on sidebar width */
                    width: '300px',
                    background: 'white', 
                    boxShadow: '0 5px 20px rgba(0,0,0,0.2)', 
                    borderRadius: '12px', 
                    zIndex: 99999, /* High Z-Index */
                    border: '1px solid #ddd',
                    overflow: 'hidden'
                }}>
                    <div style={{ padding: '15px', background: '#f8f9fa', borderBottom: '1px solid #eee', fontWeight: 'bold', color:'#333' }}>
                        Notifications
                        <button onClick={() => setShowNotif(false)} style={{float:'right', background:'none', border:'none', cursor:'pointer'}}>✕</button>
                    </div>
                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                        {notifications.length === 0 ? (
                            <div style={{ padding: '20px', color: '#999', textAlign:'center', fontSize: '0.9rem' }}>No new messages.</div>
                        ) : (
                            notifications.map(n => (
                                <div key={n.id} className="notification-item">
                                    <div style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', color:'#333' }}>
                                        {n.type === 'mail' ? '💌' : (n.type === 'warning' ? '⚠️' : (n.type === 'success' ? '🔥' : 'ℹ️'))} {n.title}
                                    </div>
                                    <div style={{ margin: '4px 0 0 0', color: '#666', fontSize:'0.85rem' }}>{n.message}</div>
                                </div>
                            ))
                        )}
                    </div>
                </div>,
                document.body
            )}
        </div>
      </div>

      <div style={{ padding: '0 0 20px 0', flexShrink: 0 }}>
        <button onClick={handleNewChat} className="primary-btn" style={{width: '100%', justifyContent:'center'}}>+ New Topic</button>
      </div>

      {/* STREAK & HEALTH */}
      <div style={{ flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#333', padding: '12px', marginBottom: '10px', borderRadius: '8px', border: '1px solid #444' }}>
            <span style={{ fontSize: '1.5rem', marginRight: '10px' }}>🔥</span>
            <div style={{ textAlign: 'left' }}>
                <div style={{ color: '#fff', fontWeight: 'bold', fontSize: '1.1rem' }}>{streak} Day Streak</div>
                <div style={{ color: '#aaa', fontSize: '0.75rem' }}>Keep it up!</div>
            </div>
        </div>

        <div style={{ padding: '12px', marginBottom: '15px', background: '#2d2d2d', borderRadius: '8px', borderLeft: `4px solid ${getRiskColor()}` }}>
            <div style={{ fontSize: '0.7rem', color: '#aaa', textTransform: 'uppercase', marginBottom: '5px', letterSpacing:'0.5px' }}>Account Health</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'white', fontWeight: 'bold' }}>{riskData.level === 'Low' ? '🔥 Excellent' : (riskData.level === 'Medium' ? '✋ Steady' : '⚠️ At Risk')}</span>
                {riskData.level === 'High' && <button onClick={() => setShowRescueModal(true)} style={{ background: '#ff6b6b', border: 'none', color: 'white', padding: '4px 10px', borderRadius: '4px', fontSize: '0.75rem', cursor: 'pointer' }}>Fix</button>}
            </div>
        </div>
      </div>

      {/* HISTORY LIST */}
      <div className="sidebar-nav" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        <div style={{ padding: '10px 0 5px 0', fontSize: '0.75rem', color: '#888', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing:'1px' }}>Recent Learning</div>
        
        {history.map((item) => (
            <div 
                key={item.id} 
                className="nav-item history-item" 
                onClick={() => handleHistoryClick(item.id, item.topic)}
                style={{
                    position: 'relative',
                    paddingRight: '30px' /* Make room for delete button */
                }}
            >
               <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display:'block', width:'100%' }}>
                   📄 {item.topic}
               </span>
               <button 
                   onClick={(e) => handleDeleteTopic(e, item.id)} 
                   className="sidebar-delete-btn"
                   title="Delete Topic"
               >
                   🗑
               </button>
            </div>
        ))}
      </div>

      {/* FOOTER & XP */}
      <div style={{ marginTop: 'auto', flexShrink: 0, paddingTop:'15px', borderTop:'1px solid #333' }}>
          <div style={{ padding: '15px', background: '#252526', borderRadius: '10px', marginBottom: '15px' }}>
             <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>
                <span>Lvl {level}</span><span>{xp} XP</span>
             </div>
             <div style={{ width: '100%', height: '6px', background: '#444', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${xpProgress}%`, height: '100%', background: 'linear-gradient(90deg, #4285f4, #9b51e0)', transition: 'width 0.5s ease' }}></div>
             </div>
          </div>
          
          <div className="sidebar-footer" style={{display:'flex', flexDirection:'column', gap:'5px', borderTop:'none'}}>
            <NavLink to="/profile" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>⚙️ Settings</NavLink>
            <button onClick={handleLogout} className="nav-item" style={{color: '#ff6b6b', justifyContent:'flex-start'}}>🚪 Logout</button>
          </div>
      </div>
    </div>
  );
};

export default Sidebar;