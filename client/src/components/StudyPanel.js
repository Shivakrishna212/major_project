import React, { useState } from 'react';
import ChatInterface from './ChatInterface';
import NotesEditor from './NotesEditor';

const StudyPanel = ({ attemptId, nodeTitle, contextContent, lessonImageUrl }) => {
    const [activeTab, setActiveTab] = useState('notes'); // 'notes' or 'chat'

    if (!nodeTitle) return <div className="sidebar-placeholder">Select a lesson to start working.</div>;

    return (
        <div className="sidebar-wrapper" style={{ display: 'flex', flexDirection: 'column', height: '100%', borderLeft: '1px solid #ddd', background: '#fff' }}>
            
            {/* TABS HEADER */}
            <div className="sidebar-tabs" style={{ display: 'flex', borderBottom: '1px solid #ddd' }}>
                <button 
                    style={{ flex: 1, padding: '15px', border: 'none', background: activeTab === 'notes' ? '#fff' : '#f5f5f5', borderBottom: activeTab === 'notes' ? '2px solid #6c5ce7' : 'none', cursor: 'pointer', fontWeight: 'bold' }}
                    onClick={() => setActiveTab('notes')}
                >
                    📝 Notes
                </button>
                <button 
                    style={{ flex: 1, padding: '15px', border: 'none', background: activeTab === 'chat' ? '#fff' : '#f5f5f5', borderBottom: activeTab === 'chat' ? '2px solid #6c5ce7' : 'none', cursor: 'pointer', fontWeight: 'bold' }}
                    onClick={() => setActiveTab('chat')}
                >
                    💬 Mentor
                </button>
            </div>

            {/* TAB CONTENT */}
            <div className="sidebar-content" style={{ flex: 1, overflow: 'hidden' }}>
                {activeTab === 'notes' ? (
                    <NotesEditor 
                        attemptId={attemptId} 
                        nodeTitle={nodeTitle} 
                        lessonImageUrl={lessonImageUrl} 
                    />
                ) : (
                    <ChatInterface 
                        attemptId={attemptId} 
                        nodeTitle={nodeTitle} 
                        contextContent={contextContent} 
                    />
                )}
            </div>
        </div>
    );
};

export default StudyPanel;