import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm'; 

const NotesEditor = ({ attemptId, nodeTitle, lessonImageUrl }) => {
    const [content, setContent] = useState("");
    const [viewMode, setViewMode] = useState('edit'); // 'edit' or 'preview'
    const [status, setStatus] = useState('saved'); 
    
    const saveTimeoutRef = useRef(null);
    const textareaRef = useRef(null); // Reference to text area for cursor position

    // 1. Load Notes
    useEffect(() => {
        const fetchNotes = async () => {
            if (!nodeTitle) return;
            setStatus('loading');
            try {
                const res = await fetch('http://127.0.0.1:5000/api/get_notes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ attempt_id: attemptId, node_title: nodeTitle })
                });
                const data = await res.json();
                setContent(data.content || "");
                setStatus('saved');
            } catch (err) { console.error(err); }
        };
        fetchNotes();
    }, [attemptId, nodeTitle]);

    // 2. Auto-Save Logic
    const handleChange = (val) => {
        setContent(val);
        setStatus('unsaved');
        if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = setTimeout(() => { saveToBackend(val); }, 2000);
    };

    const saveToBackend = async (textToSave) => {
        setStatus('saving');
        try {
            await fetch('http://127.0.0.1:5000/api/save_notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ attempt_id: attemptId, node_title: nodeTitle, content: textToSave })
            });
            setStatus('saved');
        } catch (err) { setStatus('error'); }
    };

    // --- NEW: IMAGE HELPERS ---
    
    const insertTextAtCursor = (textToInsert) => {
        const textarea = textareaRef.current;
        if (!textarea) {
            // If not focused, just append to end
            handleChange(content + textToInsert);
            return;
        }

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const prevText = content;
        
        const newText = prevText.substring(0, start) + textToInsert + prevText.substring(end);
        handleChange(newText);
        
        // Restore focus
        setTimeout(() => {
            textarea.focus();
            textarea.selectionStart = textarea.selectionEnd = start + textToInsert.length;
        }, 0);
    };

    const handleAddImageUrl = () => {
        const url = prompt("Paste image URL:");
        if (url) insertTextAtCursor(`\n![Image](${url})\n`);
    };

    const handleAddLessonDiagram = () => {
        if (lessonImageUrl) {
            insertTextAtCursor(`\n![Lesson Diagram](${lessonImageUrl})\n`);
        } else {
            alert("No diagram available for this lesson.");
        }
    };

    return (
        <div className="notes-container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* TOOLBAR */}
            <div className="notes-toolbar" style={{ padding: '8px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fafafa', gap: '10px' }}>
                
                <div className="toggle-group">
                    <button className={`toggle-btn ${viewMode === 'edit' ? 'active' : ''}`} onClick={() => setViewMode('edit')}>✏️ Edit</button>
                    <button className={`toggle-btn ${viewMode === 'preview' ? 'active' : ''}`} onClick={() => setViewMode('preview')}>👁️ Preview</button>
                </div>

                {/* IMAGE BUTTONS */}
                {viewMode === 'edit' && (
                    <div style={{ display: 'flex', gap: '5px' }}>
                        <button className="toggle-btn" title="Insert Image URL" onClick={handleAddImageUrl}>📷</button>
                        {lessonImageUrl && (
                            <button className="toggle-btn" title="Insert Current Lesson Diagram" onClick={handleAddLessonDiagram}>📉</button>
                        )}
                    </div>
                )}

                <div style={{ fontSize: '0.75rem', color: status === 'saving' ? '#ff9800' : '#ccc', marginLeft: 'auto' }}>
                    {status === 'saving' ? 'Saving...' : (status === 'saved' ? '✔' : '...')}
                </div>
            </div>

            {/* EDITOR AREA */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '15px' }}>
                {viewMode === 'edit' ? (
                    <textarea 
                        ref={textareaRef}
                        value={content}
                        onChange={(e) => handleChange(e.target.value)}
                        placeholder="# My Notes\n\nType here..."
                        style={{ width: '100%', height: '100%', border: 'none', outline: 'none', resize: 'none', fontFamily: 'monospace', fontSize: '14px', lineHeight: '1.5' }}
                    />
                ) : (
                    <div className="markdown-preview markdown-content">
                        {content ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                        ) : (
                            <p style={{ color: '#999', fontStyle: 'italic' }}>Nothing to preview...</p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default NotesEditor;