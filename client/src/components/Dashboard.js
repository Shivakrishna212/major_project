import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext'; 
import '../App.css'; 

const Dashboard = () => {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth(); 

  // Suggestions chips
  const suggestions = [
    { label: "⚛️ Quantum Physics", query: "Quantum Physics" },
    { label: "🎨 Renaissance Art", query: "Renaissance Art History" },
    { label: "🧬 DNA Structure", query: "Structure of DNA" },
    { label: "💰 Intro to Economics", query: "Basic Economics" }
  ];

  const handleStartTopic = async (selectedTopic) => {
    const topicToSend = selectedTopic || topic;
    if (!topicToSend.trim()) return;
    
    setLoading(true);

    try {
      console.log("🚀 Requesting Roadmap for:", topicToSend);

      // ✅ FIX: Use the correct endpoint '/api/generate_roadmap'
      const response = await fetch('http://127.0.0.1:5000/api/generate_roadmap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            topic: topicToSend,
            user_id: user ? user.id : null,
            level: "Beginner" // Default level
        }), 
      });

      const data = await response.json();
      console.log("✅ Server Response:", data);

      if (data.attempt_id) {
        // ✅ FIX: Navigate to the specific URL /roadmap/:id
        navigate(`/roadmap/${data.attempt_id}`, { 
          state: { 
            attemptId: data.attempt_id, 
            definition: { 
                topic: data.topic,
                definition: "Loading your custom roadmap..." 
            } 
          } 
        });
      } else {
        alert("Error: " + (data.error || "Could not start topic"));
      }

    } catch (error) {
      console.error("Network Error:", error);
      alert("Could not connect to Backend. Is 'python app.py' running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="main-content-centered"> 
      
      <div className="hero">
        {/* Personalized Greeting */}
        <h1 className="gradient-text">
            Hello, {user?.name ? user.name.split(' ')[0] : "Student"}
        </h1>
        <h2 style={{color: '#444746', fontWeight: '400'}}>What do you want to learn today?</h2>
      </div>

      {/* SEARCH INPUT AREA */}
      <div className="input-area-large">
        <input 
          type="text" 
          value={topic} 
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Enter a topic (e.g., 'Machine Learning')..."
          onKeyPress={(e) => e.key === 'Enter' && handleStartTopic()}
          disabled={loading}
        />
        <button 
            className="send-btn" 
            onClick={() => handleStartTopic()} 
            disabled={!topic || loading}
        >
            {loading ? <div className="spinner-small"></div> : "➤"}
        </button>
      </div>

      {/* SUGGESTION CHIPS */}
      <div className="suggestions-container">
        {suggestions.map((item, index) => (
            <button 
                key={index} 
                className="suggestion-chip" 
                onClick={() => handleStartTopic(item.query)}
                disabled={loading}
            >
                {item.label}
            </button>
        ))}
      </div>

    </div>
  );
};

export default Dashboard;