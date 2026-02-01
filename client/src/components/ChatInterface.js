import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm'; 
import '../App.css';

const ChatInterface = ({ attemptId, nodeTitle, contextContent }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  
  // ✅ NEW: Track if the user has actually started chatting
  // This prevents the page from auto-scrolling to the bottom on load.
  const userHasInteracted = useRef(false);

  // 1. Load Chat History
  useEffect(() => {
    const fetchChatHistory = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5000/api/get_node_chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ attempt_id: attemptId, node_title: nodeTitle })
        });
        const data = await res.json();
        setMessages(data.messages || []);
      } catch (err) { console.error("Failed to load chat", err); }
    };

    if (attemptId && nodeTitle) {
        fetchChatHistory();
    }
  }, [attemptId, nodeTitle]);

  // 2. Auto-scroll ONLY if user has interacted
  useEffect(() => {
    if (userHasInteracted.current) {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    // ✅ Mark interaction so auto-scroll starts working
    userHasInteracted.current = true;

    const userText = input;
    setInput(""); 
    setLoading(true);

    const tempId = Date.now();
    setMessages(prev => [...prev, { id: tempId, sender: 'user', text: userText }]);

    try {
      const res = await fetch('http://127.0.0.1:5000/api/send_chat_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            attempt_id: attemptId, 
            node_title: nodeTitle, 
            message: userText,
            topic_context: contextContent 
        })
      });
      
      const data = await res.json();
      
      if (data.user_message && data.ai_message) {
          setMessages(prev => [
              ...prev.filter(m => m.id !== tempId),
              data.user_message,
              data.ai_message
          ]);
      }
    } catch (err) { 
        console.error("Send failed", err);
    } finally { 
        setLoading(false); 
    }
  };

  const handleDelete = async (msgId) => {
    if (!window.confirm("Delete this question and the AI's answer?")) return;

    setMessages(prev => {
        const index = prev.findIndex(m => m.id === msgId);
        if (index === -1) return prev;
        const nextMsg = prev[index + 1];
        if (nextMsg && nextMsg.sender === 'ai') {
            return prev.filter(m => m.id !== msgId && m.id !== nextMsg.id);
        }
        return prev.filter(m => m.id !== msgId);
    });

    try {
        await fetch('http://127.0.0.1:5000/api/delete_chat_interaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: msgId })
        });
    } catch (err) { console.error("Delete API failed", err); }
  };

  return (
    <div className="chat-container">
      {/* HEADER */}
      <div className="chat-header">
        <h3>💬 AI Tutor</h3>
        <span style={{ fontSize: '0.8rem', color: '#666' }}>
            Ask doubts about <strong>{nodeTitle}</strong>
        </span>
      </div>

      {/* MESSAGES AREA */}
      <div className="chat-messages">
        {messages.length === 0 && (
            <div style={{ textAlign: 'center', color: '#999', marginTop: '40px', fontSize: '0.9rem' }}>
                No questions yet.<br/>Ask me to explain, summarize, or give examples!
            </div>
        )}

        {messages.map((msg) => (
            <div key={msg.id} className={`chat-bubble-wrapper ${msg.sender}`}>
                {msg.sender === 'user' && (
                    <button 
                        className="delete-chat-btn" 
                        onClick={() => handleDelete(msg.id)}
                        title="Delete conversation thread"
                    >
                        🗑
                    </button>
                )}
                
                <div className={`chat-bubble ${msg.sender}`}>
                    <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.text}
                        </ReactMarkdown>
                    </div>
                </div>
            </div>
        ))}

        {loading && (
            <div className="chat-bubble-wrapper ai">
                <div className="chat-bubble ai typing">
                    <span className="dot">.</span><span className="dot">.</span><span className="dot">.</span>
                </div>
            </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* INPUT AREA */}
      <div className="chat-input-area">
        <input 
            type="text" 
            placeholder="Type your doubt here..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={loading}
        />
        <button 
            className="send-chat-btn" 
            onClick={handleSend} 
            disabled={loading || !input.trim()}
        >
            ➤
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;