import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Context for user and app state
const AppContext = createContext();

const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

// Components
const Timer = ({ onComplete, isActive, timeLeft, totalTime }) => {
  const progress = ((totalTime - timeLeft) / totalTime) * 100;
  
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="timer-container">
      <div className="timer-circle">
        <svg className="timer-svg" viewBox="0 0 100 100">
          <circle
            className="timer-track"
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            opacity="0.2"
          />
          <circle
            className="timer-progress"
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 45}`}
            strokeDashoffset={`${2 * Math.PI * 45 * (1 - progress / 100)}`}
            transform="rotate(-90 50 50)"
          />
        </svg>
        <div className="timer-display">
          <div className="timer-time">{formatTime(timeLeft)}</div>
          <div className="timer-status">{isActive ? 'Focus Time' : 'Paused'}</div>
        </div>
      </div>
    </div>
  );
};

const TaskItem = ({ task, onToggle, onDelete }) => {
  return (
    <div className={`task-item ${task.status === 'completed' ? 'completed' : ''}`}>
      <div className="task-content">
        <button
          className={`task-checkbox ${task.status === 'completed' ? 'checked' : ''}`}
          onClick={() => onToggle(task.id)}
        >
          {task.status === 'completed' && (
            <svg className="check-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          )}
        </button>
        <div className="task-text">
          <h4 className={task.status === 'completed' ? 'line-through' : ''}>{task.title}</h4>
          {task.description && (
            <p className={task.status === 'completed' ? 'line-through opacity-60' : 'opacity-75'}>
              {task.description}
            </p>
          )}
        </div>
      </div>
      <button
        className="delete-button"
        onClick={() => onDelete(task.id)}
      >
        <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9zM4 5a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
        </svg>
      </button>
    </div>
  );
};

const StatsCard = ({ title, value, subtitle, className = "" }) => {
  return (
    <div className={`stats-card ${className}`}>
      <div className="stats-content">
        <div className="stats-value">{value}</div>
        <div className="stats-title">{title}</div>
        {subtitle && <div className="stats-subtitle">{subtitle}</div>}
      </div>
    </div>
  );
};

const PomodoroSession = () => {
  const { user, updateUserStats } = useAppContext();
  const [isActive, setIsActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(25 * 60); // 25 minutes in seconds
  const [sessionType, setSessionType] = useState('focus');
  const [currentSessionId, setCurrentSessionId] = useState(null);

  const sessionTypes = {
    focus: { duration: 25 * 60, label: 'Focus Time', next: 'short_break' },
    short_break: { duration: 5 * 60, label: 'Short Break', next: 'focus' },
    long_break: { duration: 15 * 60, label: 'Long Break', next: 'focus' }
  };

  useEffect(() => {
    let interval = null;
    if (isActive && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft(timeLeft => timeLeft - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      handleSessionComplete();
    }
    return () => clearInterval(interval);
  }, [isActive, timeLeft]);

  const startTimer = async () => {
    if (!currentSessionId) {
      try {
        const response = await axios.post(`${API}/users/${user.id}/focus-sessions`, {
          timer_type: sessionType,
          duration_minutes: sessionTypes[sessionType].duration / 60
        });
        setCurrentSessionId(response.data.id);
      } catch (error) {
        console.error('Error starting session:', error);
        return;
      }
    }
    setIsActive(true);
  };

  const pauseTimer = () => {
    setIsActive(false);
  };

  const resetTimer = () => {
    setIsActive(false);
    setTimeLeft(sessionTypes[sessionType].duration);
    setCurrentSessionId(null);
  };

  const handleSessionComplete = async () => {
    setIsActive(false);
    
    if (currentSessionId && sessionType === 'focus') {
      try {
        await axios.put(`${API}/users/${user.id}/focus-sessions/${currentSessionId}/complete`);
        updateUserStats();
      } catch (error) {
        console.error('Error completing session:', error);
      }
    }
    
    // Auto-switch to next session type
    const nextType = sessionTypes[sessionType].next;
    setSessionType(nextType);
    setTimeLeft(sessionTypes[nextType].duration);
    setCurrentSessionId(null);
  };

  return (
    <div className="pomodoro-container">
      <div className="session-type-selector">
        {Object.entries(sessionTypes).map(([type, config]) => (
          <button
            key={type}
            className={`session-type-btn ${sessionType === type ? 'active' : ''}`}
            onClick={() => {
              setSessionType(type);
              setTimeLeft(config.duration);
              setIsActive(false);
              setCurrentSessionId(null);
            }}
          >
            {config.label}
          </button>
        ))}
      </div>

      <Timer 
        isActive={isActive}
        timeLeft={timeLeft}
        totalTime={sessionTypes[sessionType].duration}
        onComplete={handleSessionComplete}
      />

      <div className="timer-controls">
        {!isActive ? (
          <button className="timer-btn primary" onClick={startTimer}>
            {timeLeft === sessionTypes[sessionType].duration ? 'Start' : 'Resume'}
          </button>
        ) : (
          <button className="timer-btn secondary" onClick={pauseTimer}>
            Pause
          </button>
        )}
        <button className="timer-btn secondary" onClick={resetTimer}>
          Reset
        </button>
      </div>

      {user.subscription_tier === 'free' && (
        <div className="premium-upsell">
          <div className="upsell-content">
            <h4>Want Custom Timer Lengths?</h4>
            <p>Unlock 90/15 deep work sessions, custom sounds, and more with Premium!</p>
            <button className="upgrade-btn">Upgrade to Premium</button>
          </div>
        </div>
      )}
    </div>
  );
};

const TaskManager = () => {
  const { user, tasks, setTasks, updateUserStats } = useAppContext();
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDescription, setNewTaskDescription] = useState('');

  const addTask = async (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    try {
      const response = await axios.post(`${API}/users/${user.id}/tasks`, {
        title: newTaskTitle.trim(),
        description: newTaskDescription.trim()
      });

      setTasks([response.data, ...tasks]);
      setNewTaskTitle('');
      setNewTaskDescription('');
    } catch (error) {
      console.error('Error adding task:', error);
    }
  };

  const toggleTask = async (taskId) => {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    try {
      const response = await axios.put(`${API}/users/${user.id}/tasks/${taskId}`, {
        status: task.status === 'completed' ? 'pending' : 'completed'
      });

      setTasks(tasks.map(t => t.id === taskId ? response.data : t));
      
      if (response.data.status === 'completed') {
        updateUserStats();
      }
    } catch (error) {
      console.error('Error updating task:', error);
    }
  };

  const deleteTask = async (taskId) => {
    try {
      await axios.delete(`${API}/users/${user.id}/tasks/${taskId}`);
      setTasks(tasks.filter(t => t.id !== taskId));
    } catch (error) {
      console.error('Error deleting task:', error);
    }
  };

  const pendingTasks = tasks.filter(t => t.status === 'pending');
  const completedTasks = tasks.filter(t => t.status === 'completed');

  return (
    <div className="task-manager">
      <form onSubmit={addTask} className="task-form">
        <div className="form-group">
          <input
            type="text"
            value={newTaskTitle}
            onChange={(e) => setNewTaskTitle(e.target.value)}
            placeholder="What needs to be done?"
            className="task-input"
            maxLength={100}
          />
        </div>
        <div className="form-group">
          <textarea
            value={newTaskDescription}
            onChange={(e) => setNewTaskDescription(e.target.value)}
            placeholder="Add a description (optional)"
            className="task-textarea"
            rows={2}
            maxLength={200}
          />
        </div>
        <button type="submit" className="add-task-btn">
          <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          Add Task (+10 XP)
        </button>
      </form>

      <div className="task-sections">
        {pendingTasks.length > 0 && (
          <div className="task-section">
            <h3 className="section-title">Pending Tasks ({pendingTasks.length})</h3>
            <div className="task-list">
              {pendingTasks.map(task => (
                <TaskItem
                  key={task.id}
                  task={task}
                  onToggle={toggleTask}
                  onDelete={deleteTask}
                />
              ))}
            </div>
          </div>
        )}

        {completedTasks.length > 0 && (
          <div className="task-section">
            <h3 className="section-title">Completed Tasks ({completedTasks.length})</h3>
            <div className="task-list">
              {completedTasks.slice(0, 5).map(task => (
                <TaskItem
                  key={task.id}
                  task={task}
                  onToggle={toggleTask}
                  onDelete={deleteTask}
                />
              ))}
              {completedTasks.length > 5 && (
                <p className="more-tasks">+{completedTasks.length - 5} more completed tasks</p>
              )}
            </div>
          </div>
        )}

        {tasks.length === 0 && (
          <div className="empty-state">
            <div className="empty-content">
              <svg className="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
              <h3>No tasks yet!</h3>
              <p>Create your first task to get started on your productivity journey.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const Dashboard = () => {
  const { user, dashboardData, theme } = useAppContext();

  if (!dashboardData) {
    return <div className="loading">Loading dashboard...</div>;
  }

  const { today_stats, level_progress, recent_achievements } = dashboardData;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="user-info">
          <h1 className="welcome-text">Welcome back, {user.name}!</h1>
          <div className={`theme-badge theme-${theme.primary}`}>
            Today's Theme: {theme.name}
          </div>
        </div>

        <div className="level-card">
          <div className="level-info">
            <div className="level-number">Level {user.level}</div>
            <div className="level-progress">
              <div 
                className="level-progress-bar"
                style={{ width: `${level_progress.progress_percentage}%` }}
              ></div>
            </div>
            <div className="level-text">
              {level_progress.xp_to_next_level} XP to Level {user.level + 1}
            </div>
          </div>
          <div className="total-xp">{user.total_xp} XP</div>
        </div>
      </div>

      <div className="stats-grid">
        <StatsCard
          title="Today's Tasks"
          value={today_stats.tasks_completed}
          className="stats-card-tasks"
        />
        <StatsCard
          title="Focus Sessions"
          value={today_stats.focus_sessions_completed}
          className="stats-card-focus"
        />
        <StatsCard
          title="Focus Time"
          value={`${today_stats.total_focus_time}m`}
          className="stats-card-time"
        />
        <StatsCard
          title="Current Streak"
          value={user.current_streak}
          subtitle="days"
          className="stats-card-streak"
        />
      </div>

      {recent_achievements.length > 0 && (
        <div className="achievements-section">
          <h3 className="section-title">Recent Achievements</h3>
          <div className="achievements-list">
            {recent_achievements.map(achievement => (
              <div key={achievement.id} className="achievement-card">
                <div className="achievement-icon">🏆</div>
                <div className="achievement-content">
                  <h4>{achievement.title}</h4>
                  <p>{achievement.description}</p>
                  <span className="achievement-xp">+{achievement.xp_reward} XP</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const App = () => {
  const [user, setUser] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [theme, setTheme] = useState({ name: 'Default', primary: 'purple', secondary: 'indigo' });
  const [currentView, setCurrentView] = useState('dashboard');
  const [loading, setLoading] = useState(true);

  const updateUserStats = async () => {
    if (!user) return;
    
    try {
      const [dashboardResponse, tasksResponse] = await Promise.all([
        axios.get(`${API}/users/${user.id}/dashboard`),
        axios.get(`${API}/users/${user.id}/tasks`)
      ]);
      
      setDashboardData(dashboardResponse.data);
      setUser(dashboardResponse.data.user);
      setTasks(tasksResponse.data);
      setTheme(dashboardResponse.data.theme);
    } catch (error) {
      console.error('Error updating stats:', error);
    }
  };

  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Get daily theme
        const themeResponse = await axios.get(`${API}/theme`);
        setTheme(themeResponse.data);

        // Create or get user (demo user for now)
        const userResponse = await axios.post(`${API}/users`, {
          name: 'Demo User',
          email: 'demo@focusflow.com'
        });
        setUser(userResponse.data);

        // Get dashboard data and tasks
        const [dashboardResponse, tasksResponse] = await Promise.all([
          axios.get(`${API}/users/${userResponse.data.id}/dashboard`),
          axios.get(`${API}/users/${userResponse.data.id}/tasks`)
        ]);
        
        setDashboardData(dashboardResponse.data);
        setTasks(tasksResponse.data);
        setTheme(dashboardResponse.data.theme);
        
      } catch (error) {
        console.error('Error initializing app:', error);
      } finally {
        setLoading(false);
      }
    };

    initializeApp();
  }, []);

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading FocusFlow...</p>
      </div>
    );
  }

  const contextValue = {
    user,
    setUser,
    tasks,
    setTasks,
    dashboardData,
    setDashboardData,
    theme,
    setTheme,
    updateUserStats
  };

  return (
    <AppContext.Provider value={contextValue}>
      <div className={`app theme-${theme.primary}`}>
        <nav className="navigation">
          <div className="nav-brand">
            <h2>FocusFlow</h2>
            {user.subscription_tier === 'premium' && (
              <span className="premium-badge">PREMIUM</span>
            )}
          </div>
          
          <div className="nav-items">
            <button
              className={`nav-item ${currentView === 'dashboard' ? 'nav-item-active' : 'nav-item-inactive'}`}
              onClick={() => setCurrentView('dashboard')}
            >
              <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
              </svg>
              Dashboard
            </button>
            <button
              className={`nav-item ${currentView === 'tasks' ? 'nav-item-active' : 'nav-item-inactive'}`}
              onClick={() => setCurrentView('tasks')}
            >
              <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h12a1 1 0 011 1v8a1 1 0 01-1 1H4a1 1 0 01-1-1V8z" clipRule="evenodd" />
              </svg>
              Tasks
            </button>
            <button
              className={`nav-item ${currentView === 'focus' ? 'nav-item-active' : 'nav-item-inactive'}`}
              onClick={() => setCurrentView('focus')}
            >
              <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              Focus
            </button>
          </div>
        </nav>

        <main className="main-content">
          {currentView === 'dashboard' && <Dashboard />}
          {currentView === 'tasks' && <TaskManager />}
          {currentView === 'focus' && <PomodoroSession />}
        </main>
      </div>
    </AppContext.Provider>
  );
};

export default App;