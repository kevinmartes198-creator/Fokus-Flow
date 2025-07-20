import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Helper function to check if user has premium access
const isPremiumUser = (subscriptionTier) => {
  return ['premium', 'premium_monthly', 'premium_yearly', 'premium_lifetime'].includes(subscriptionTier);
};

// Language translations
const translations = {
  en: {
    // Navigation
    dashboard: "Dashboard",
    tasks: "Tasks",
    focus: "Focus",
    projects: "Projects",
    
    // Dashboard
    welcomeBack: "Welcome back",
    todayTheme: "Today's Theme",
    productivityTheme: "Productivity Theme",
    level: "Level",
    xpToNext: "XP to Level",
    todayTasks: "Today's Tasks",
    focusSessions: "Focus Sessions",
    focusTime: "Focus Time",
    currentStreak: "Current Streak",
    days: "days",
    yourPlan: "Your Plan",
    recentAchievements: "Recent Achievements",
    
    // Premium Features
    customTimers: "Custom Timers",
    adaptiveThemes: "Adaptive Themes",
    premiumSounds: "Premium Sounds",
    xpBonus: "XP Bonus",
    enabled: "Enabled",
    premiumOnly: "Premium only",
    standardXp: "Standard XP",
    upgradeToPremium: "Upgrade to Premium - Unlock all features for $9.99/month",
    
    // Projects & Kanban
    myProjects: "My Projects",
    createProject: "Create Project",
    projectName: "Project Name",
    projectDescription: "Project Description (optional)",
    projectColor: "Theme Color",
    kanbanBoard: "Kanban Board",
    todo: "To Do",
    inProgress: "In Progress",
    done: "Done",
    addTask: "Add Task",
    taskTitle: "Task Title",
    taskDescription: "Task Description (optional)",
    priority: "Priority",
    dueDate: "Due Date",
    low: "Low",
    medium: "Medium",
    high: "High",
    
    // Tasks
    whatTodo: "What needs to be done?",
    addDescription: "Add a description (optional)",
    addTaskXp: "Add Task (+{xp} XP)",
    premiumBonus: "20% Bonus!",
    pendingTasks: "Pending Tasks",
    completedTasks: "Completed Tasks",
    moreTasks: "+{count} more completed tasks",
    noTasksYet: "No tasks yet!",
    createFirstTask: "Create your first task to get started on your productivity journey.",
    
    // Timer
    focusTime: "Focus Time",
    shortBreak: "Short Break",
    longBreak: "Long Break",
    paused: "Paused",
    start: "Start",
    resume: "Resume",
    pause: "Pause",
    reset: "Reset",
    
    // Custom Timers
    customTimersTitle: "Custom Timers",
    createTimer: "Create Timer",
    useTimer: "Use",
    deleteTimer: "Delete",
    usingTimer: "Using",
    useDefaultTimer: "Use Default Timer",
    
    // Premium Upsell
    wantCustomTimers: "Want Custom Timer Lengths?",
    unlockFeatures: "Unlock 90/15 deep work sessions, productivity themes, and 20% XP bonus with Premium!",
    upgradeBtn: "Upgrade to Premium - $9.99/month",
    
    // Subscription Modal
    upgradeToPremium: "Upgrade to Premium",
    premiumFeaturesInclude: "Premium Features Include:",
    customTimerLengths: "Custom timer lengths (90/15 min deep work sessions)",
    productivityBasedThemes: "Productivity-based adaptive themes",
    premiumNotifications: "Premium sound notifications",
    xpBonusFeature: "20% XP bonus on all activities",
    advancedAnalytics: "Advanced analytics and insights",
    premiumMonthly: "Premium Monthly",
    subscribeNow: "Subscribe Now",
    processing: "Processing...",
    premiumNote: "✨ Start your premium journey today and unlock your full productivity potential!",
    
    // Custom Timer Modal
    editTimer: "Edit Timer",
    createCustomTimer: "Create Custom Timer",
    timerName: "Timer Name",
    timerNamePlaceholder: "e.g., Deep Work Session",
    focusTimeMin: "Focus Time (minutes)",
    shortBreakMin: "Short Break (minutes)",
    longBreakMin: "Long Break (minutes)",
    save: "Save",
    cancel: "Cancel",
    
    // Premium Features Section
    premiumFeatures: "Premium Features",
    locked: "🔒 Locked",
    
    // Referrals
    referralDashboard: "Referral Dashboard",
    yourReferralCode: "Your Referral Code",
    shareCode: "Share this code with friends",
    earnCommission: "Earn ${amount} for each premium referral",
    totalEarnings: "Total Earnings",
    totalReferrals: "Total Referrals",
    referralLink: "Referral Link",
    copyLink: "Copy Link",
    linkCopied: "Link copied to clipboard!",
    socialShare: "Share on Social Media",
    facebookShare: "Share on Facebook",
    twitterShare: "Share on Twitter",
    linkedinShare: "Share on LinkedIn",
    howItWorks: "How It Works",
    step1: "1. Share your referral code or link",
    step2: "2. Friends sign up using your code",
    step3: "3. When they upgrade to premium, you earn ${amount}",
    step4: "4. Instant payout to your account",
    recentReferrals: "Recent Referrals",
    noReferralsYet: "No referrals yet. Start sharing to earn!",
    
    // Common
    loading: "Loading...",
    error: "Error",
    success: "Success",
    close: "Close",
    delete: "Delete",
    edit: "Edit",
    create: "Create",
    update: "Update",
    view: "View",
    back: "Back"
  },
  // Spanish translations
  es: {
    dashboard: "Panel",
    tasks: "Tareas",
    focus: "Enfoque",
    projects: "Proyectos",
    welcomeBack: "Bienvenido de nuevo",
    todayTheme: "Tema de hoy",
    productivityTheme: "Tema de productividad",
    level: "Nivel",
    xpToNext: "XP al siguiente nivel",
    todayTasks: "Tareas de hoy",
    focusSessions: "Sesiones de enfoque",
    focusTime: "Tiempo de enfoque",
    currentStreak: "Racha actual",
    days: "días",
    yourPlan: "Tu plan",
    recentAchievements: "Logros recientes",
    myProjects: "Mis Proyectos",
    createProject: "Crear Proyecto",
    kanbanBoard: "Tablero Kanban",
    todo: "Por Hacer",
    inProgress: "En Progreso", 
    done: "Terminado",
    customTimers: "Temporizadores personalizados",
    adaptiveThemes: "Temas adaptativos",
    premiumSounds: "Sonidos premium",
    xpBonus: "Bono XP",
    enabled: "Habilitado",
    premiumOnly: "Solo premium",
    standardXp: "XP estándar",
    whatTodo: "¿Qué necesitas hacer?",
    addDescription: "Añadir descripción (opcional)",
    addTask: "Añadir tarea",
    addTaskXp: "Añadir tarea (+{xp} XP)",
    premiumBonus: "¡Bonus 20%!",
    pendingTasks: "Tareas pendientes",
    completedTasks: "Tareas completadas",
    moreTasks: "+{count} tareas completadas más",
    noTasksYet: "¡No hay tareas aún!",
    createFirstTask: "Crea tu primera tarea para comenzar tu viaje de productividad.",
    shortBreak: "Descanso corto",
    longBreak: "Descanso largo",
    paused: "Pausado",
    start: "Iniciar",
    resume: "Reanudar",
    pause: "Pausar",
    reset: "Reiniciar",
    customTimersTitle: "Temporizadores personalizados",
    createTimer: "Crear temporizador",
    useTimer: "Usar",
    deleteTimer: "Eliminar",
    usingTimer: "Usando",
    useDefaultTimer: "Usar temporizador predeterminado",
    wantCustomTimers: "¿Quieres duraciones de temporizador personalizadas?",
    unlockFeatures: "¡Desbloquea sesiones de trabajo profundo de 90/15, temas de productividad y bonificación de XP del 20% con Premium!",
    upgradeBtn: "Actualizar a Premium - €9.99/mes",
    upgradeToPremium: "Actualizar a Premium",
    premiumFeaturesInclude: "Las funciones Premium incluyen:",
    customTimerLengths: "Duraciones de temporizador personalizadas (sesiones de trabajo profundo de 90/15 min)",
    productivityBasedThemes: "Temas adaptativos basados en productividad",
    premiumNotifications: "Notificaciones de sonido premium",
    xpBonusFeature: "Bonificación de XP del 20% en todas las actividades",
    advancedAnalytics: "Análisis e insights avanzados",
    premiumMonthly: "Premium mensual",
    subscribeNow: "Suscribirse ahora",
    processing: "Procesando...",
    premiumNote: "✨ ¡Comienza tu viaje premium hoy y desbloquea todo tu potencial de productividad!",
    editTimer: "Editar temporizador",
    createCustomTimer: "Crear temporizador personalizado",
    timerName: "Nombre del temporizador",
    timerNamePlaceholder: "ej., Sesión de trabajo profundo",
    focusTimeMin: "Tiempo de enfoque (minutos)",
    shortBreakMin: "Descanso corto (minutos)",
    longBreakMin: "Descanso largo (minutos)",
    save: "Guardar",
    cancel: "Cancelar",
    premiumFeatures: "Funciones Premium",
    locked: "🔒 Bloqueado",
    referralDashboard: "Panel de referencias",
    yourReferralCode: "Tu código de referencia",
    shareCode: "Comparte este código con amigos",
    earnCommission: "Gana €{amount} por cada referencia premium",
    totalEarnings: "Ganancias totales",
    totalReferrals: "Referencias totales",
    referralLink: "Enlace de referencia",
    copyLink: "Copiar enlace",
    linkCopied: "¡Enlace copiado al portapapeles!",
    socialShare: "Compartir en redes sociales",
    facebookShare: "Compartir en Facebook",
    twitterShare: "Compartir en Twitter",
    linkedinShare: "Compartir en LinkedIn",
    howItWorks: "Cómo funciona",
    step1: "1. Comparte tu código o enlace de referencia",
    step2: "2. Los amigos se registran usando tu código",
    step3: "3. Cuando actualicen a premium, ganas €{amount}",
    step4: "4. Pago instantáneo a tu cuenta",
    recentReferrals: "Referencias recientes",
    noReferralsYet: "No hay referencias aún. ¡Comienza a compartir para ganar!",
    loading: "Cargando...",
    error: "Error",
    success: "Éxito",
    close: "Cerrar",
    delete: "Eliminar",
    edit: "Editar",
    create: "Crear",
    update: "Actualizar",
    view: "Ver",
    back: "Atrás"
  },
  // French translations
  fr: {
    dashboard: "Tableau de bord",
    tasks: "Tâches",
    focus: "Focus",
    projects: "Projets", 
    welcomeBack: "Content de vous revoir",
    todayTheme: "Thème du jour",
    productivityTheme: "Thème de productivité",
    level: "Niveau",
    xpToNext: "XP au suivant",
    todayTasks: "Tâches d'aujourd'hui",
    focusSessions: "Sessions de focus",
    focusTime: "Temps de focus",
    currentStreak: "Série actuelle",
    days: "jours",
    yourPlan: "Votre plan",
    recentAchievements: "Réalisations récentes",
    myProjects: "Mes Projets",
    createProject: "Créer un Projet",
    kanbanBoard: "Tableau Kanban",
    todo: "À Faire",
    inProgress: "En Cours",
    done: "Terminé",
    customTimers: "Minuteurs personnalisés",
    adaptiveThemes: "Thèmes adaptatifs",
    premiumSounds: "Sons premium",
    xpBonus: "Bonus XP",
    enabled: "Activé",
    premiumOnly: "Premium uniquement",
    standardXp: "XP standard",
    whatTodo: "Que faut-il faire ?",
    addDescription: "Ajouter une description (facultatif)",
    addTask: "Ajouter une tâche",
    addTaskXp: "Ajouter tâche (+{xp} XP)",
    premiumBonus: "Bonus 20% !",
    pendingTasks: "Tâches en attente",
    completedTasks: "Tâches terminées",
    moreTasks: "+{count} tâches terminées de plus",
    noTasksYet: "Pas encore de tâches !",
    createFirstTask: "Créez votre première tâche pour commencer votre voyage de productivité.",
    shortBreak: "Pause courte",
    longBreak: "Pause longue",
    paused: "En pause",
    start: "Démarrer",
    resume: "Reprendre",
    pause: "Pause",
    reset: "Réinitialiser",
    customTimersTitle: "Minuteurs personnalisés",
    createTimer: "Créer un minuteur",
    useTimer: "Utiliser",
    deleteTimer: "Supprimer",
    usingTimer: "Utilisation",
    useDefaultTimer: "Utiliser le minuteur par défaut",
    wantCustomTimers: "Vous voulez des durées de minuteur personnalisées ?",
    unlockFeatures: "Débloquez les sessions de travail profond 90/15, les thèmes de productivité et le bonus XP de 20% avec Premium !",
    upgradeBtn: "Passer à Premium - €9,99/mois",
    upgradeToPremium: "Passer à Premium",
    premiumFeaturesInclude: "Les fonctionnalités Premium incluent :",
    customTimerLengths: "Durées de minuteur personnalisées (sessions de travail profond de 90/15 min)",
    productivityBasedThemes: "Thèmes adaptatifs basés sur la productivité",
    premiumNotifications: "Notifications sonores premium",
    xpBonusFeature: "Bonus XP de 20% sur toutes les activités",
    advancedAnalytics: "Analyses et insights avancés",
    premiumMonthly: "Premium mensuel",
    subscribeNow: "S'abonner maintenant",
    processing: "Traitement...",
    premiumNote: "✨ Commencez votre voyage premium aujourd'hui et débloquez tout votre potentiel de productivité !",
    editTimer: "Modifier le minuteur",
    createCustomTimer: "Créer un minuteur personnalisé",
    timerName: "Nom du minuteur",
    timerNamePlaceholder: "ex., Session de travail profond",
    focusTimeMin: "Temps de focus (minutes)",
    shortBreakMin: "Pause courte (minutes)",
    longBreakMin: "Pause longue (minutes)",
    save: "Enregistrer",
    cancel: "Annuler",
    premiumFeatures: "Fonctionnalités Premium",
    locked: "🔒 Verrouillé",
    referralDashboard: "Tableau de bord des références",
    yourReferralCode: "Votre code de référence",
    shareCode: "Partagez ce code avec des amis",
    earnCommission: "Gagnez €{amount} pour chaque référence premium",
    totalEarnings: "Gains totaux",
    totalReferrals: "Références totales",
    referralLink: "Lien de référence",
    copyLink: "Copier le lien",
    linkCopied: "Lien copié dans le presse-papiers !",
    socialShare: "Partager sur les réseaux sociaux",
    facebookShare: "Partager sur Facebook",
    twitterShare: "Partager sur Twitter",
    linkedinShare: "Partager sur LinkedIn",
    howItWorks: "Comment ça marche",
    step1: "1. Partagez votre code ou lien de référence",
    step2: "2. Les amis s'inscrivent en utilisant votre code",
    step3: "3. Quand ils passent à premium, vous gagnez €{amount}",
    step4: "4. Paiement instantané sur votre compte",
    recentReferrals: "Références récentes",
    noReferralsYet: "Pas encore de références. Commencez à partager pour gagner !",
    loading: "Chargement...",
    error: "Erreur",
    success: "Succès",
    close: "Fermer",
    delete: "Supprimer",
    edit: "Modifier",
    create: "Créer",
    update: "Mettre à jour",
    view: "Voir",
    back: "Retour"
  },
  // German translations
  de: {
    dashboard: "Dashboard",
    tasks: "Aufgaben",
    focus: "Fokus",
    projects: "Projekte",
    welcomeBack: "Willkommen zurück",
    todayTheme: "Heutiges Thema",
    productivityTheme: "Produktivitätsthema",
    level: "Level",
    xpToNext: "XP zum nächsten Level",
    todayTasks: "Heutige Aufgaben",
    focusSessions: "Fokus-Sessions",
    focusTime: "Fokuszeit",
    currentStreak: "Aktuelle Serie",
    days: "Tage",
    yourPlan: "Ihr Plan",
    recentAchievements: "Aktuelle Erfolge",
    myProjects: "Meine Projekte",
    createProject: "Projekt Erstellen",
    kanbanBoard: "Kanban Board",
    todo: "Zu Erledigen",
    inProgress: "In Bearbeitung",
    done: "Erledigt",
    customTimers: "Benutzerdefinierte Timer",
    adaptiveThemes: "Adaptive Themen",
    premiumSounds: "Premium-Sounds",
    xpBonus: "XP-Bonus",
    enabled: "Aktiviert",
    premiumOnly: "Nur Premium",
    standardXp: "Standard XP",
    whatTodo: "Was muss erledigt werden?",
    addDescription: "Beschreibung hinzufügen (optional)",
    addTask: "Aufgabe hinzufügen",
    addTaskXp: "Aufgabe hinzufügen (+{xp} XP)",
    premiumBonus: "20% Bonus!",
    pendingTasks: "Ausstehende Aufgaben",
    completedTasks: "Erledigte Aufgaben",
    moreTasks: "+{count} weitere erledigte Aufgaben",
    noTasksYet: "Noch keine Aufgaben!",
    createFirstTask: "Erstellen Sie Ihre erste Aufgabe, um Ihre Produktivitätsreise zu beginnen.",
    shortBreak: "Kurze Pause",
    longBreak: "Lange Pause",
    paused: "Pausiert",
    start: "Starten",
    resume: "Fortsetzen",
    pause: "Pausieren",
    reset: "Zurücksetzen",
    customTimersTitle: "Benutzerdefinierte Timer",
    createTimer: "Timer erstellen",
    useTimer: "Verwenden",
    deleteTimer: "Löschen",
    usingTimer: "Verwende",
    useDefaultTimer: "Standard-Timer verwenden",
    wantCustomTimers: "Möchten Sie benutzerdefinierte Timer-Längen?",
    unlockFeatures: "Schalten Sie 90/15 Deep-Work-Sessions, Produktivitätsthemen und 20% XP-Bonus mit Premium frei!",
    upgradeBtn: "Auf Premium upgraden - €9,99/Monat",
    upgradeToPremium: "Auf Premium upgraden",
    premiumFeaturesInclude: "Premium-Features umfassen:",
    customTimerLengths: "Benutzerdefinierte Timer-Längen (90/15 Min Deep-Work-Sessions)",
    productivityBasedThemes: "Produktivitätsbasierte adaptive Themen",
    premiumNotifications: "Premium-Sound-Benachrichtigungen",
    xpBonusFeature: "20% XP-Bonus bei allen Aktivitäten",
    advancedAnalytics: "Erweiterte Analysen und Einblicke",
    premiumMonthly: "Premium Monatlich",
    subscribeNow: "Jetzt abonnieren",
    processing: "Verarbeitung...",
    premiumNote: "✨ Starten Sie heute Ihre Premium-Reise und entfesseln Sie Ihr volles Produktivitätspotenzial!",
    editTimer: "Timer bearbeiten",
    createCustomTimer: "Benutzerdefinierten Timer erstellen",
    timerName: "Timer-Name",
    timerNamePlaceholder: "z.B. Deep Work Session",
    focusTimeMin: "Fokuszeit (Minuten)",
    shortBreakMin: "Kurze Pause (Minuten)",
    longBreakMin: "Lange Pause (Minuten)",
    save: "Speichern",
    cancel: "Abbrechen",
    premiumFeatures: "Premium-Features",
    locked: "🔒 Gesperrt",
    referralDashboard: "Empfehlungs-Dashboard",
    yourReferralCode: "Ihr Empfehlungscode",
    shareCode: "Teilen Sie diesen Code mit Freunden",
    earnCommission: "Verdienen Sie €{amount} für jede Premium-Empfehlung",
    totalEarnings: "Gesamtverdienst",
    totalReferrals: "Gesamte Empfehlungen",
    referralLink: "Empfehlungslink",
    copyLink: "Link kopieren",
    linkCopied: "Link in Zwischenablage kopiert!",
    socialShare: "In sozialen Medien teilen",
    facebookShare: "Auf Facebook teilen",
    twitterShare: "Auf Twitter teilen",
    linkedinShare: "Auf LinkedIn teilen",
    howItWorks: "Wie es funktioniert",
    step1: "1. Teilen Sie Ihren Empfehlungscode oder Link",
    step2: "2. Freunde melden sich mit Ihrem Code an",
    step3: "3. Wenn sie auf Premium upgraden, verdienen Sie €{amount}",
    step4: "4. Sofortige Auszahlung auf Ihr Konto",
    recentReferrals: "Aktuelle Empfehlungen",
    noReferralsYet: "Noch keine Empfehlungen. Beginnen Sie zu teilen, um zu verdienen!",
    loading: "Wird geladen...",
    error: "Fehler",
    success: "Erfolg",
    close: "Schließen",
    delete: "Löschen",
    edit: "Bearbeiten",
    create: "Erstellen",
    update: "Aktualisieren",
    view: "Anzeigen",
    back: "Zurück"
  }
};

// User Context for global state management
const UserContext = createContext();

export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

// Language Context
const LanguageContext = createContext();

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

// Main App Component
function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState('en');
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  
  // Initialize user - you'll need to implement this based on your auth system
  useEffect(() => {
    initializeUser();
  }, []);

  const initializeUser = async () => {
    try {
      // For demo purposes, we'll create a default user
      // In production, you'd get this from your authentication system
      const defaultUser = {
        id: "demo-user-id",
        name: "Demo User",
        email: "demo@focusflow.app",
        subscription_tier: "free",
        total_xp: 0,
        level: 1,
        current_streak: 0,
        total_referrals: 0,
        total_commission_earned: 0.0,
        referral_code: "DEMO123"
      };
      
      setUser(defaultUser);
      setLoading(false);
    } catch (error) {
      console.error('Error initializing user:', error);
      setError('Failed to initialize user');
      setLoading(false);
    }
  };

  const t = (key, params = {}) => {
    let translation = translations[language]?.[key] || translations.en[key] || key;
    
    // Replace parameters in translation
    Object.keys(params).forEach(param => {
      translation = translation.replace(`{${param}}`, params[param]);
    });
    
    return translation;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-purple-600 font-medium">{t('loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">⚠️</div>
          <p className="text-red-600 font-medium">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <UserContext.Provider value={{ user, setUser }}>
      <LanguageContext.Provider value={{ language, setLanguage, t }}>
        <div className="App">
          <FocusFlowApp 
            currentView={currentView} 
            setCurrentView={setCurrentView}
            showSubscriptionModal={showSubscriptionModal}
            setShowSubscriptionModal={setShowSubscriptionModal}
          />
        </div>
      </LanguageContext.Provider>
    </UserContext.Provider>
  );
}

// Projects & Kanban Board Component
const ProjectsView = () => {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [kanbanData, setKanbanData] = useState(null);
  const [draggedTask, setDraggedTask] = useState(null);
  const { user } = useUser();
  const { t } = useLanguage();

  useEffect(() => {
    if (user) {
      fetchProjects();
    }
  }, [user]);

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API}/users/${user.id}/projects`);
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  };

  const fetchKanbanBoard = async (projectId) => {
    try {
      const response = await axios.get(`${API}/projects/${projectId}/kanban`);
      setKanbanData(response.data);
    } catch (error) {
      console.error('Error fetching kanban board:', error);
    }
  };

  const createProject = async (projectData) => {
    try {
      const response = await axios.post(`${API}/users/${user.id}/projects`, projectData);
      setProjects([response.data, ...projects]);
      setShowCreateProject(false);
    } catch (error) {
      console.error('Error creating project:', error);
    }
  };

  const createTask = async (taskData) => {
    try {
      const response = await axios.post(`${API}/projects/${selectedProject}/tasks`, taskData);
      await fetchKanbanBoard(selectedProject);
      setShowCreateTask(false);
    } catch (error) {
      console.error('Error creating task:', error);
    }
  };

  const handleDragStart = (e, task) => {
    setDraggedTask(task);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e, column) => {
    e.preventDefault();
    if (!draggedTask) return;

    try {
      await axios.put(`${API}/tasks/kanban/${draggedTask.id}/move`, {
        column: column,
        position: 0 // Add to top of column for simplicity
      });
      
      await fetchKanbanBoard(selectedProject);
      setDraggedTask(null);
    } catch (error) {
      console.error('Error moving task:', error);
    }
  };

  if (!user) return null;

  if (selectedProject && kanbanData) {
    return (
      <div className="projects-view">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => {setSelectedProject(null); setKanbanData(null);}}
              className="p-2 hover:bg-purple-100 rounded-lg transition-colors"
            >
              ← {t('back')}
            </button>
            <h1 className="text-2xl font-bold text-gray-800">
              📋 {kanbanData.project.name}
            </h1>
            {kanbanData.project.description && (
              <p className="text-gray-600">{kanbanData.project.description}</p>
            )}
          </div>
          <button
            onClick={() => setShowCreateTask(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            + {t('addTask')}
          </button>
        </div>

        <div className="kanban-board grid grid-cols-3 gap-6">
          {['todo', 'in_progress', 'done'].map(column => (
            <div 
              key={column}
              className="kanban-column bg-white rounded-xl p-4 shadow-sm"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, column)}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">
                  {column === 'todo' && `📝 ${t('todo')}`}
                  {column === 'in_progress' && `⚡ ${t('inProgress')}`}
                  {column === 'done' && `✅ ${t('done')}`}
                </h3>
                <span className="bg-gray-100 px-2 py-1 rounded-full text-sm">
                  {kanbanData.board[column].length}
                </span>
              </div>
              
              <div className="space-y-3">
                {kanbanData.board[column].map(task => (
                  <div
                    key={task.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, task)}
                    className="kanban-task bg-gray-50 p-3 rounded-lg cursor-move hover:shadow-md transition-shadow"
                  >
                    <h4 className="font-medium text-gray-800 mb-1">{task.title}</h4>
                    {task.description && (
                      <p className="text-sm text-gray-600 mb-2">{task.description}</p>
                    )}
                    <div className="flex items-center justify-between text-xs">
                      <span className={`priority-badge ${task.priority}`}>
                        {task.priority === 'high' && '🔴'} 
                        {task.priority === 'medium' && '🟡'}
                        {task.priority === 'low' && '🟢'}
                        {task.priority}
                      </span>
                      {task.due_date && (
                        <span className="text-gray-500">
                          Due: {new Date(task.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {showCreateTask && (
          <CreateTaskModal
            projectId={selectedProject}
            onClose={() => setShowCreateTask(false)}
            onSubmit={createTask}
          />
        )}
      </div>
    );
  }

  return (
    <div className="projects-view">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">📁 {t('myProjects')}</h1>
        <button
          onClick={() => setShowCreateProject(true)}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
        >
          + {t('createProject')}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(project => (
          <div 
            key={project.id}
            className="project-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => {
              setSelectedProject(project.id);
              fetchKanbanBoard(project.id);
            }}
          >
            <div className="flex items-center mb-3">
              <div 
                className="w-4 h-4 rounded-full mr-3"
                style={{backgroundColor: project.color}}
              ></div>
              <h3 className="font-semibold text-gray-800">{project.name}</h3>
            </div>
            
            {project.description && (
              <p className="text-gray-600 mb-4">{project.description}</p>
            )}
            
            <div className="flex items-center text-sm text-gray-500">
              <span>📅 {new Date(project.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
        
        {projects.length === 0 && (
          <div className="col-span-full text-center py-12">
            <div className="text-gray-400 mb-4">📁</div>
            <p className="text-gray-600 mb-4">No projects yet!</p>
            <button
              onClick={() => setShowCreateProject(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              {t('createProject')}
            </button>
          </div>
        )}
      </div>

      {showCreateProject && (
        <CreateProjectModal
          onClose={() => setShowCreateProject(false)}
          onSubmit={createProject}
        />
      )}
    </div>
  );
};

// Create Project Modal
const CreateProjectModal = ({ onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    color: '#8b5cf6'
  });
  const { t } = useLanguage();

  const colors = [
    '#8b5cf6', '#10b981', '#3b82f6', '#f59e0b', 
    '#ef4444', '#8b5a2b', '#6b7280', '#ec4899'
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    onSubmit(formData);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2 className="text-xl font-bold mb-4">{t('createProject')}</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('projectName')}
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              placeholder="My Awesome Project"
              required
            />
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('projectDescription')}
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              rows="3"
              placeholder="Optional project description..."
            />
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('projectColor')}
            </label>
            <div className="flex gap-2">
              {colors.map(color => (
                <button
                  key={color}
                  type="button"
                  className={`w-8 h-8 rounded-full border-2 ${formData.color === color ? 'border-gray-400' : 'border-transparent'}`}
                  style={{backgroundColor: color}}
                  onClick={() => setFormData({...formData, color})}
                />
              ))}
            </div>
          </div>
          
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              {t('cancel')}
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            >
              {t('create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Create Task Modal
const CreateTaskModal = ({ projectId, onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: '',
    project_id: projectId
  });
  const { t } = useLanguage();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.title.trim()) return;
    onSubmit({
      ...formData,
      due_date: formData.due_date || null
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2 className="text-xl font-bold mb-4">{t('addTask')}</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('taskTitle')}
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              placeholder="Task title..."
              required
            />
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('taskDescription')}
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              rows="3"
              placeholder="Optional task description..."
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('priority')}
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({...formData, priority: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              >
                <option value="low">🟢 {t('low')}</option>
                <option value="medium">🟡 {t('medium')}</option>
                <option value="high">🔴 {t('high')}</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('dueDate')}
              </label>
              <input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({...formData, due_date: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>
          
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              {t('cancel')}
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            >
              {t('addTask')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Main FocusFlow App Component with all existing functionality
const FocusFlowApp = ({ currentView, setCurrentView, showSubscriptionModal, setShowSubscriptionModal }) => {
  const { user, setUser } = useUser();
  const { language, setLanguage, t } = useLanguage();

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100">
      {/* Top Banner */}
      <TopReferralBanner />
      
      {/* Main Navigation */}
      <nav className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <div className="focus-flow-logo">
                <span className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
                  🎯 FocusFlow
                </span>
              </div>
            </div>
            
            <div className="nav-items">
              <button
                className={`nav-item ${currentView === 'dashboard' ? 'nav-item-active' : 'nav-item-inactive'}`}
                onClick={() => setCurrentView('dashboard')}
              >
                <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
                </svg>
                {t('dashboard')}
              </button>
              
              <button
                className={`nav-item ${currentView === 'projects' ? 'nav-item-active' : 'nav-item-inactive'}`}
                onClick={() => setCurrentView('projects')}
              >
                <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z" />
                </svg>
                📁 {t('projects')}
              </button>
              
              <button
                className={`nav-item ${currentView === 'tasks' ? 'nav-item-active' : 'nav-item-inactive'}`}
                onClick={() => setCurrentView('tasks')}
              >
                <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h12a1 1 0 011 1v8a1 1 0 01-1 1H4a1 1 0 01-1-1V8z" clipRule="evenodd" />
                </svg>
                {t('tasks')}
              </button>
              
              <button
                className={`nav-item ${currentView === 'focus' ? 'nav-item-active' : 'nav-item-inactive'}`}
                onClick={() => setCurrentView('focus')}
              >
                <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                </svg>
                {t('focus')}
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'projects' && <ProjectsView />}
        {currentView === 'tasks' && <TasksView />}
        {currentView === 'focus' && <FocusView />}
      </main>

      {/* Subscription Modal */}
      {showSubscriptionModal && (
        <SubscriptionModal onClose={() => setShowSubscriptionModal(false)} />
      )}
    </div>
  );
};

// Placeholder components for existing functionality
const TopReferralBanner = () => {
  const { user } = useUser();
  const { language, setLanguage, t } = useLanguage();
  
  return (
    <div className="bg-gradient-to-r from-green-500 to-emerald-600 text-white p-3">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="font-semibold">💰 {t('totalEarnings')}: €{user?.total_commission_earned || 0}</span>
          <span>🤝 {t('referralCode')}: {user?.referral_code || 'DEMO123'}</span>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-sm">{t('language')}:</span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-white/20 text-white border-white/30 rounded px-2 py-1 text-sm"
          >
            <option value="en">🇺🇸 EN</option>
            <option value="es">🇪🇸 ES</option>
            <option value="fr">🇫🇷 FR</option>
            <option value="de">🇩🇪 DE</option>
          </select>
        </div>
      </div>
    </div>
  );
};

const Dashboard = () => {
  const { user } = useUser();
  const { t } = useLanguage();
  
  return (
    <div className="dashboard-view">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">
        {t('welcomeBack')}, {user?.name || 'User'}! 👋
      </h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="stat-card bg-white p-6 rounded-xl shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('level')}</p>
              <p className="text-2xl font-bold text-purple-600">{user?.level || 1}</p>
            </div>
            <div className="text-3xl">⭐</div>
          </div>
        </div>
        
        <div className="stat-card bg-white p-6 rounded-xl shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total XP</p>
              <p className="text-2xl font-bold text-green-600">{user?.total_xp || 0}</p>
            </div>
            <div className="text-3xl">🎯</div>
          </div>
        </div>
        
        <div className="stat-card bg-white p-6 rounded-xl shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('currentStreak')}</p>
              <p className="text-2xl font-bold text-orange-600">{user?.current_streak || 0} {t('days')}</p>
            </div>
            <div className="text-3xl">🔥</div>
          </div>
        </div>
      </div>
      
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">Welcome to FocusFlow!</h2>
        <p className="text-gray-600 mb-4">
          Your productivity journey starts here. Use the navigation above to access:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="feature-card p-4 border rounded-lg">
            <div className="text-2xl mb-2">📁</div>
            <h3 className="font-semibold">Projects</h3>
            <p className="text-sm text-gray-600">Organize your work with Kanban boards</p>
          </div>
          <div className="feature-card p-4 border rounded-lg">
            <div className="text-2xl mb-2">✅</div>
            <h3 className="font-semibold">Tasks</h3>
            <p className="text-sm text-gray-600">Simple task management with XP rewards</p>
          </div>
          <div className="feature-card p-4 border rounded-lg">
            <div className="text-2xl mb-2">⏰</div>
            <h3 className="font-semibold">Focus</h3>
            <p className="text-sm text-gray-600">Pomodoro timer for deep work sessions</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const TasksView = () => {
  const { t } = useLanguage();
  
  return (
    <div className="tasks-view">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">📝 {t('tasks')}</h1>
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <p className="text-gray-600">Simple task management view would go here.</p>
      </div>
    </div>
  );
};

const FocusView = () => {
  const { t } = useLanguage();
  
  return (
    <div className="focus-view">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">⏰ {t('focus')}</h1>
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <p className="text-gray-600">Pomodoro timer would go here.</p>
      </div>
    </div>
  );
};

const SubscriptionModal = ({ onClose }) => {
  const { t } = useLanguage();
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2 className="text-xl font-bold mb-4">{t('upgradeToPremium')}</h2>
        <p>Subscription modal content would go here.</p>
        <button
          onClick={onClose}
          className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
        >
          {t('close')}
        </button>
      </div>
    </div>
  );
};

export default App;