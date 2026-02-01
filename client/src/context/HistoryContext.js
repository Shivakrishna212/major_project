import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const HistoryContext = createContext();

export const useHistory = () => useContext(HistoryContext);

export const HistoryProvider = ({ children }) => {
  const [history, setHistory] = useState([]);

  const refreshHistory = async () => {
    try {
      // Add timestamp to prevent caching
      const res = await axios.get(`http://localhost:5000/api/my_topics?t=${Date.now()}`, { 
        withCredentials: true 
      });
      setHistory(res.data);
    } catch (err) {
      console.error("Failed to load history");
    }
  };

  // --- NEW FUNCTION: OPTIMISTIC UPDATE ---
  const addLocalTopic = (newTopic) => {
    // Add the new topic to the TOP of the list immediately
    setHistory(prevHistory => [newTopic, ...prevHistory]);
  };

  useEffect(() => {
    refreshHistory();
  }, []);

  return (
    // We expose 'addLocalTopic' to the rest of the app
    <HistoryContext.Provider value={{ history, refreshHistory, addLocalTopic }}>
      {children}
    </HistoryContext.Provider>
  );
};