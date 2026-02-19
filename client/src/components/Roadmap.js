import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm'; 
import rehypeHighlight from 'rehype-highlight'; 
import 'highlight.js/styles/atom-one-dark.css'; 
import '../App.css'; 

// Components
import LevelUpModal from './LevelUpModal';
import StudyPanel from './StudyPanel'; 

// --- MATH HELPER ---
const getNodeX = (index) => {
    const startX = 300; 
    const hGap = 150; 
    const mod = index % 4;
    
    if (mod === 0 || mod === 2) return startX; 
    if (mod === 1) return startX + hGap;       
    if (mod === 3) return startX - hGap;       
    return startX;
};

// --- WIGGLY PATH GENERATOR ---
const getWigglyPath = (count) => {
    if (count <= 0) return "";
    const startY = 80; 
    const vGap = 160; 
    let path = `M ${getNodeX(0)} ${startY}`;
    
    for (let i = 0; i < count - 1; i++) {
        const currentX = getNodeX(i); 
        const nextX = getNodeX(i + 1); 
        const currentY = startY + (i * vGap); 
        const nextY = startY + ((i + 1) * vGap);
        
        const cp1X = currentX; 
        const cp1Y = currentY + (vGap / 2); 
        const cp2X = nextX; 
        const cp2Y = currentY + (vGap / 2);
        
        path += ` C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${nextX} ${nextY}`;
    }
    return path;
};

// --- MAP RENDERER ---
const WigglyMap = ({ items, onNodeClick, completedIndices, lockedIndices = [], colorTheme = 'blue' }) => {
    const mapHeight = (items.length * 160) + 100; 
    const themes = {
        blue: { pathColor: '#bbdefb', primary: '#2196f3', shadow: 'rgba(33, 150, 243, 0.4)' },
        purple: { pathColor: '#d1c4e9', primary: '#6c5ce7', shadow: 'rgba(108, 92, 231, 0.4)' }
    };
    const theme = themes[colorTheme] || themes.blue;

    return (
        <div className="roadmap-path-container" style={{ position: 'relative', width: '600px', margin: '0 auto', height: `${mapHeight}px` }}>
            <svg width="600" height={mapHeight} style={{ position: 'absolute', top: 0, left: 0, zIndex: 0, overflow: 'visible' }}>
                <path d={getWigglyPath(items.length)} fill="none" stroke={theme.pathColor} strokeWidth="5" strokeDasharray="15,10" strokeLinecap="round" />
            </svg>
            {items.map((item, index) => {
                const isCompleted = completedIndices.includes(index);
                const isLocked = lockedIndices.includes(index);
                let nodeStyle = {};
                
                if (isLocked) {
                    nodeStyle = { background: '#f5f5f5', borderColor: '#ddd', color: '#ccc', cursor: 'not-allowed' };
                } else if (isCompleted) {
                    nodeStyle = { background: theme.primary, borderColor: theme.primary, color: 'white', boxShadow: `0 0 15px ${theme.shadow}` };
                } else {
                    nodeStyle = { background: 'white', borderColor: theme.primary, color: theme.primary, borderWidth: '4px' };
                }

                return (
                    <div key={index} className="roadmap-node-wrapper" style={{ zIndex: 2, height: '160px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'absolute', top: `${index * 160}px`, left: `${getNodeX(index)}px`, transform: 'translateX(-50%)' }}>
                        <div style={{ position: 'relative' }}>
                            <div className={`node-circle`} onClick={() => { if (!isLocked) onNodeClick(item, index); }} style={nodeStyle}>
                                {isCompleted ? "✔" : index + 1}
                            </div>
                            <div className={`node-details-popup ${index % 4 === 1 ? 'popup-left' : 'popup-right'}`} style={{ width: '200px' }}>
                                <h3 style={{ margin: '0 0 5px 0', fontSize: '1rem', color: '#333' }}>{item.title}</h3>
                                {isLocked && <div style={{color:'#999', fontSize:'0.75rem'}}>🔒 Locked</div>}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

// --- MAIN COMPONENT ---
const Roadmap = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Data State
  const [currentAttemptId, setCurrentAttemptId] = useState(location.state?.attemptId || null);
  const [currentDefinition, setCurrentDefinition] = useState(location.state?.definition || null);
  
  // View State
  const [viewMode, setViewMode] = useState('main_map'); 
  const [mainRoadmap, setMainRoadmap] = useState([]); 
  const [subRoadmap, setSubRoadmap] = useState([]);   
  const [completedMainIndices, setCompletedMainIndices] = useState([]);
  const [completedSubIndices, setCompletedSubIndices] = useState([]); 
  const [activeModule, setActiveModule] = useState(null); 
  const [selectedNode, setSelectedNode] = useState(null); 
  const [selectedNodeIndex, setSelectedNodeIndex] = useState(null); 
  
  // Content State
  const [lessonContent, setLessonContent] = useState(""); 
  const [lessonImageUrl, setLessonImageUrl] = useState(""); 
  const [quizData, setQuizData] = useState([]); 
  const [loading, setLoading] = useState(false);
  const [hasDeepDived, setHasDeepDived] = useState(false); 

  // Quiz State
  const [quizStarted, setQuizStarted] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);
  const [failedQuestions, setFailedQuestions] = useState([]); 
  const [userAnswers, setUserAnswers] = useState({}); 
  const [isRegenerating, setIsRegenerating] = useState(false); 
  const [showLevelUp, setShowLevelUp] = useState(false);
  const [newLevel, setNewLevel] = useState(1);

  // Resize Logic
  const sidebarWidthRef = useRef(450); 
  const [sidebarWidth, setSidebarWidth] = useState(450); 
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = useCallback((e) => {
      e.preventDefault();
      setIsResizing(true);
      const startX = e.clientX;
      const startWidth = sidebarWidthRef.current;
      const doDrag = (moveEvent) => {
          const delta = startX - moveEvent.clientX;
          const newWidth = startWidth + delta;
          if (newWidth > 300 && newWidth < 800) {
              sidebarWidthRef.current = newWidth; 
              setSidebarWidth(newWidth); 
          }
      };
      const stopDrag = () => {
          setIsResizing(false);
          document.removeEventListener('mousemove', doDrag);
          document.removeEventListener('mouseup', stopDrag);
          document.body.style.cursor = '';
          document.body.style.userSelect = ''; 
      };
      document.addEventListener('mousemove', doDrag);
      document.addEventListener('mouseup', stopDrag);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none'; 
  }, []);

  // Navigation Listener
  useEffect(() => {
      if (location.state?.attemptId) {
          setCurrentAttemptId(location.state.attemptId);
          setCurrentDefinition(location.state.definition);
          setViewMode('main_map'); 
          setSubRoadmap([]); 
          setActiveModule(null); 
          setHasDeepDived(false);
      }
  }, [location.state]);

  // Fetch Logic
  useEffect(() => {
    let activeId = currentAttemptId;
    if (!activeId) {
        const saved = localStorage.getItem('roadmap_state');
        if (saved) { 
            activeId = JSON.parse(saved).attemptId; 
            setCurrentAttemptId(activeId); 
        } else { 
            navigate('/dashboard'); 
            return; 
        }
    }
    localStorage.setItem('roadmap_state', JSON.stringify({ attemptId: activeId, definition: currentDefinition }));

    const fetchMainMap = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://127.0.0.1:5000/api/get_roadmap', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ attempt_id: activeId }) 
            });
            const data = await res.json();
            
            if (data.roadmap) {
                setMainRoadmap(data.roadmap);
                setCompletedMainIndices(data.completed_indices || []);
                
                const def = data.definition || {};
                setCurrentDefinition({ 
                    ...def, 
                    topic: data.topic || def.topic || "Unknown Topic" 
                });
                
                if (data.completed_indices?.length > 0) setHasDeepDived(true);
            }
        } catch (e) { 
            console.error(e); 
        } finally { 
            setLoading(false); 
        }
    };
    if (activeId) fetchMainMap();
  }, [currentAttemptId, navigate]); 

  // Handlers
  const handleMainModuleClick = async (m, i) => { 
      setLoading(true); 
      setActiveModule({ ...m, index: i }); 
      setSubRoadmap([]); 
      setCompletedSubIndices([]); 
      try { 
          const res = await fetch('http://127.0.0.1:5000/api/get_sub_roadmap', { 
              method: 'POST', 
              headers: {'Content-Type': 'application/json'}, 
              body: JSON.stringify({ attempt_id: currentAttemptId, module_index: i, module_title: m.title }) 
          }); 
          const data = await res.json(); 
          setSubRoadmap(data.sub_roadmap || []); 
          setCompletedSubIndices(data.completed_indices || []); 
          setViewMode('sub_map'); 
          window.scrollTo(0, 0); 
      } catch (e) { console.error(e); } finally { setLoading(false); } 
  };

  const handleSubNodeClick = async (n, i) => { 
      setLoading(true); 
      setSelectedNode(n.title); 
      setSelectedNodeIndex(i); 
      setLessonContent(""); 
      setLessonImageUrl(""); 
      setQuizData([]); 
      setQuizStarted(false); 
      setShowResult(false); 
      setScore(0); 
      setCurrentQuestionIndex(0); 
      setUserAnswers({}); 
      try { 
          const res = await fetch('http://127.0.0.1:5000/api/get_node', { 
              method: 'POST', 
              headers: {'Content-Type': 'application/json'}, 
              body: JSON.stringify({ attempt_id: currentAttemptId, node_title: n.title, node_index: i }) 
          }); 
          const data = await res.json(); 
          setLessonContent(data.content); 
          setLessonImageUrl(data.image_url); 
          setQuizData(data.quiz || []); 
          setViewMode('lesson'); 
          window.scrollTo(0, 0); 
      } catch (e) { console.error(e); } finally { setLoading(false); } 
  };

  const handleBack = () => { 
      if (viewMode === 'lesson') { setViewMode('sub_map'); setSelectedNode(null); } 
      else { setViewMode('main_map'); setActiveModule(null); } 
      window.scrollTo(0, 0); 
  };

  const handleOptionSelect = (opt) => { setSelectedOption(opt); setUserAnswers(prev => ({ ...prev, [currentQuestionIndex]: opt })); };

  const handleSubmitAnswer = async () => { 
      if (!selectedOption) return; 
      const q = quizData[currentQuestionIndex]; 
      const ans = (q.correct_answer || q.ans || "").trim(); 
      let newScore = score;
      if (selectedOption.trim() === ans) { newScore = score + 1; setScore(newScore); } 
      else { setFailedQuestions(f => [...f, q.question]); } 

      if (currentQuestionIndex + 1 < quizData.length) { setCurrentQuestionIndex(i => i + 1); setSelectedOption(null); } 
      else { 
          setShowResult(true); 
          const passed = newScore >= (quizData.length / 2); 
          if (passed) { 
              await fetch('http://127.0.0.1:5000/api/submit_node_quiz', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ attempt_id: currentAttemptId, node_title: selectedNode, score: newScore, passed: true }) }); 
              let newSub = [...completedSubIndices]; 
              if (!completedSubIndices.includes(selectedNodeIndex)) { newSub.push(selectedNodeIndex); setCompletedSubIndices(newSub); } 
              if (newSub.length >= subRoadmap.length) { 
                  const res = await fetch('http://127.0.0.1:5000/api/mark_module_complete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ attempt_id: currentAttemptId, module_index: activeModule.index }) }); 
                  const d = await res.json(); 
                  if (d.success) setCompletedMainIndices(d.completed_modules); 
              } 
          } 
      } 
  };

  const handleRegenerateLesson = async () => { 
      setIsRegenerating(true); 
      try { 
          const res = await fetch('http://127.0.0.1:5000/api/regenerate_remedial', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ attempt_id: currentAttemptId, node_title: selectedNode, failed_questions: failedQuestions }) }); 
          const d = await res.json(); 
          if (d.success) { 
              setLessonContent(d.new_content.content); 
              setQuizData(d.new_content.quiz); 
              setQuizStarted(false); setShowResult(false); setScore(0); setCurrentQuestionIndex(0); setUserAnswers({}); setFailedQuestions([]); 
          } 
      } catch (e) { console.error(e); } 
      setIsRegenerating(false); 
  };

  const getIntroText = () => {
    if (!currentDefinition) return "";
    if (typeof currentDefinition === 'string') return currentDefinition;
    return currentDefinition.definition || currentDefinition.intro || "";
  };

  const getIntroHook = () => {
    if (currentDefinition && typeof currentDefinition === 'object' && currentDefinition.hook) {
        return currentDefinition.hook;
    }
    return "";
  };

  return (
    <div className="container roadmap-page">
      {showLevelUp && <LevelUpModal newLevel={newLevel} onClose={() => setShowLevelUp(false)} />}
      
      <div className="roadmap-header fade-in">
          {viewMode === 'main_map' && (
              <h1 style={{fontSize:'1.8rem', textAlign:'center'}}>
                  {currentDefinition?.topic || "Loading Topic..."} 
              </h1>
          )}
          {viewMode !== 'main_map' && (
              <div style={{ padding: '10px 0', borderBottom: '1px solid #eee', marginBottom: '20px' }}>
                  <button className="secondary-btn" onClick={handleBack} style={{ marginBottom: '10px' }}>
                      ← Back to {viewMode === 'lesson' ? activeModule?.title : "Main Map"}
                  </button>
                  <h2 style={{ margin: 0, color: '#333' }}>
                      {viewMode === 'sub_map' ? `Module: ${activeModule?.title}` : selectedNode}
                  </h2>
              </div>
          )}
      </div>

      {viewMode === 'main_map' && (
          <>
            {!hasDeepDived ? (
                <div className="intro-section fade-in" style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center', padding: '20px' }}>
                    
                    {currentDefinition ? (
                        <div style={{ background: 'white', padding: '40px', borderRadius: '12px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
                            {getIntroHook() && (
                                <h2 style={{ fontSize: '1.6rem', fontWeight: '300', color: '#5f6368', marginBottom: '30px', fontStyle: 'italic', fontFamily: 'Georgia, serif' }}>
                                    "{getIntroHook()}"
                                </h2>
                            )}
                            <div className="markdown-container" style={{ textAlign: 'left' }}>
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {getIntroText()}
                                </ReactMarkdown>
                            </div>
                            <div style={{marginTop:'40px'}}>
                                <button className="primary-btn" onClick={() => setHasDeepDived(true)} disabled={loading} style={{fontSize: '1.1rem', padding: '12px 30px'}}>
                                    {loading ? "Loading..." : "🚀 Start Journey"}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div style={{ padding: '50px' }}>
                            <div className="loading-spinner"></div>
                            <p style={{ marginTop: '15px', color: '#888' }}>Loading Topic Overview...</p>
                        </div>
                    )}
                </div>
            ) : (
                <div className="fade-in">
                    <p style={{textAlign:'center', color:'#666', marginBottom:'40px'}}>
                        Select a module to explore its topics.
                    </p>
                    <WigglyMap 
                        items={mainRoadmap} 
                        onNodeClick={handleMainModuleClick} 
                        completedIndices={completedMainIndices} 
                        lockedIndices={mainRoadmap.map((_, i) => i > 0 && !completedMainIndices.includes(i-1) && !completedMainIndices.includes(i) ? i : -1).filter(i => i !== -1)} 
                        colorTheme="blue"
                    />
                </div>
            )}
          </>
      )}

      {viewMode === 'sub_map' && (
          <div className="fade-in">
              <p style={{textAlign:'center', color:'#666', marginBottom:'40px'}}>
                  Deep Dive into <strong>{activeModule?.title}</strong>
              </p>
              {loading ? (
                  <div style={{textAlign:'center', marginTop:'50px'}}>
                      <div className="loading-spinner"></div>
                  </div>
              ) : (
                  <WigglyMap items={subRoadmap} onNodeClick={handleSubNodeClick} completedIndices={completedSubIndices} colorTheme="purple"/>
              )}
          </div>
      )}

      {viewMode === 'lesson' && (
          <div className="lesson-section fade-in" style={{ width: '100%', height: 'calc(100vh - 120px)', padding: 0, overflow: 'hidden', display: 'flex' }}>
              <div className="lesson-panel" style={{ flex: 1, overflowY: 'auto', padding: '20px', background: '#fff', minWidth: '300px' }}>
                  {(loading || isRegenerating) && (
                      <div style={{textAlign:'center', padding:'50px'}}>
                          <div className="loading-spinner"></div>
                          {isRegenerating && <p style={{marginTop:'20px', color:'#6c5ce7'}}>🤖 Simplifying lesson...</p>}
                      </div>
                  )}
                  {!loading && !isRegenerating && lessonContent && !quizStarted && (
                      <div className="lesson-content">
                          {/* ⚠️ Image rendering removed here; now handled by ReactMarkdown inside lessonContent */}
                          <div className="markdown-container markdown-content">
                              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{lessonContent}</ReactMarkdown>
                          </div>
                          <div style={{textAlign:'center', marginTop:'40px'}}><button className="primary-btn" onClick={() => setQuizStarted(true)}>Take Quiz</button></div>
                      </div>
                  )}
                  {quizStarted && !isRegenerating && (
                      <div className="quiz-container">
                          {!showResult ? (
                             <div className="quiz-card-active fade-in">
                                 <div className="quiz-header">Question {currentQuestionIndex + 1} / {quizData.length}</div>
                                 <h3>{quizData[currentQuestionIndex]?.question}</h3>
                                 <div className="quiz-options">{quizData[currentQuestionIndex]?.options?.map((opt, i) => <button key={i} className={`option-btn ${selectedOption === opt ? 'selected' : ''}`} onClick={() => handleOptionSelect(opt)}>{opt}</button>)}</div>
                                 <div className="quiz-footer"><button className="primary-btn" onClick={handleSubmitAnswer} disabled={!selectedOption}>Next</button></div>
                             </div>
                          ) : (
                             <div className="quiz-result fade-in" style={{ textAlign: 'left', maxWidth: '800px', margin: '0 auto' }}>
                                 <h2 style={{ textAlign: 'center' }}>{score >= (quizData.length / 2) ? "🎉 Quiz Passed!" : "⚠️ Needs Review"}</h2>
                                 <p style={{ textAlign: 'center' }}>You scored {score} out of {quizData.length}</p>
                                 <div className="quiz-review-list">{quizData.map((q, idx) => { const userAnswer = userAnswers[idx]; const correctAns = (q.correct_answer || q.ans || "").trim(); const userAnsClean = (userAnswer || "").trim(); const isCorrect = userAnsClean === correctAns; return (<div key={idx} style={{ marginBottom: '20px', padding: '15px', border: '1px solid #eee', borderRadius: '8px', background: '#fcfcfc' }}><p style={{ fontWeight: 'bold' }}>{idx + 1}. {q.question}</p><div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>{q.options.map((opt, i) => { const optClean = opt.trim(); let style = { padding: '8px', borderRadius: '4px', border: '1px solid #ddd', fontSize: '0.9rem', display: 'flex', justifyContent: 'space-between' }; if (optClean === correctAns) style = { ...style, background: '#d4edda', borderColor: '#c3e6cb', color: '#155724' }; else if (optClean === userAnsClean && !isCorrect) style = { ...style, background: '#f8d7da', borderColor: '#f5c6cb', color: '#721c24' }; return (<div key={i} style={style}><span>{opt}</span><span>{optClean === correctAns && " ✅ Correct"}{optClean === userAnsClean && !isCorrect && " 🫵 You"}</span></div>)})}</div></div>)})}</div>
                                 <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', marginTop: '30px', paddingBottom: '50px' }}>{score >= (quizData.length / 2) ? <button className="primary-btn" onClick={handleBack}>✅ Complete & Continue</button> : <><button className="secondary-btn" onClick={() => { setQuizStarted(true); setShowResult(false); setScore(0); setCurrentQuestionIndex(0); setFailedQuestions([]); setUserAnswers({}); }}>🔄 Retry Quiz</button><button className="primary-btn" style={{ background: '#ff9800', border: 'none' }} onClick={handleRegenerateLesson}>🧠 I'm Stuck - Simplify Lesson</button></>}</div>
                             </div>
                          )}
                      </div>
                  )}
              </div>
              <div className="resizer" onMouseDown={startResizing} style={{ width: '8px', cursor: 'col-resize', background: isResizing ? '#6c5ce7' : '#e0e0e0', transition: 'background 0.2s', zIndex: 10, flexShrink: 0 }} />
              <div className="sidebar-panel" style={{ width: `${sidebarWidth}px`, borderLeft: '1px solid #eee', background: '#fcfcfc', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
                  <StudyPanel attemptId={currentAttemptId} nodeTitle={selectedNode} contextContent={lessonContent} lessonImageUrl={lessonImageUrl} />
              </div>
          </div>
      )}
    </div>
  );
};

export default Roadmap;