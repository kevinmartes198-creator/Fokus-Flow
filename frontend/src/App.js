import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Language translations
const translations = {
  en: {
    // Navigation
    dashboard: "Dashboard",
    tasks: "Tasks",
    focus: "Focus",
    
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
    
    // Tasks
    whatTodo: "What needs to be done?",
    addDescription: "Add a description (optional)",
    addTask: "Add Task",
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
    cancel: "Cancel",
    updateTimer: "Update Timer",
    createTimerBtn: "Create Timer",
    
    // Payment Success
    processingPayment: "Processing your payment...",
    pleaseWait: "Please wait while we confirm your subscription.",
    welcomeToPremium: "Welcome to Premium!",
    subscriptionActivated: "Your subscription has been activated successfully.",
    amount: "Amount",
    date: "Date",
    continueToApp: "Continue to App",
    paymentFailed: "Payment Failed",
    paymentIssue: "There was an issue processing your payment. Please try again.",
    backToApp: "Back to App",
    paymentTimeout: "Payment Status Check Timed Out",
    stillProcessing: "We're still processing your payment. Please check your email for confirmation.",
    somethingWrong: "Something Went Wrong",
    contactSupport: "We encountered an error checking your payment status. Please contact support.",
    
    // Common
    loading: "Loading...",
    loadingApp: "Loading FocusFlow...",
    delete: "Delete",
    edit: "Edit",
    save: "Save",
    close: "Close"
  },
  es: {
    // Navigation
    dashboard: "Panel",
    tasks: "Tareas",
    focus: "Enfoque",
    
    // Dashboard
    welcomeBack: "Bienvenido de vuelta",
    todayTheme: "Tema de Hoy",
    productivityTheme: "Tema de Productividad",
    level: "Nivel",
    xpToNext: "XP para Nivel",
    todayTasks: "Tareas de Hoy",
    focusSessions: "Sesiones de Enfoque",
    focusTime: "Tiempo de Enfoque",
    currentStreak: "Racha Actual",
    days: "días",
    yourPlan: "Tu Plan",
    recentAchievements: "Logros Recientes",
    
    // Premium Features
    customTimers: "Temporizadores Personalizados",
    adaptiveThemes: "Temas Adaptativos",
    premiumSounds: "Sonidos Premium",
    xpBonus: "Bonificación XP",
    enabled: "Habilitado",
    premiumOnly: "Solo Premium",
    standardXp: "XP Estándar",
    upgradeToPremium: "Actualizar a Premium - Desbloquea todas las funciones por $9.99/mes",
    
    // Tasks
    whatTodo: "¿Qué necesita ser hecho?",
    addDescription: "Añadir una descripción (opcional)",
    addTask: "Añadir Tarea",
    addTaskXp: "Añadir Tarea (+{xp} XP)",
    premiumBonus: "¡20% Bonificación!",
    pendingTasks: "Tareas Pendientes",
    completedTasks: "Tareas Completadas",
    moreTasks: "+{count} tareas completadas más",
    noTasksYet: "¡Aún no hay tareas!",
    createFirstTask: "Crea tu primera tarea para comenzar tu viaje de productividad.",
    
    // Timer
    focusTime: "Tiempo de Enfoque",
    shortBreak: "Descanso Corto",
    longBreak: "Descanso Largo",
    paused: "Pausado",
    start: "Iniciar",
    resume: "Continuar",
    pause: "Pausar",
    reset: "Reiniciar",
    
    // Custom Timers
    customTimersTitle: "Temporizadores Personalizados",
    createTimer: "Crear Temporizador",
    useTimer: "Usar",
    deleteTimer: "Eliminar",
    usingTimer: "Usando",
    useDefaultTimer: "Usar Temporizador Predeterminado",
    
    // Premium Upsell
    wantCustomTimers: "¿Quieres Duraciones de Temporizador Personalizadas?",
    unlockFeatures: "¡Desbloquea sesiones de trabajo profundo de 90/15, temas de productividad y 20% de bonificación XP con Premium!",
    upgradeBtn: "Actualizar a Premium - $9.99/mes",
    
    // Subscription Modal
    upgradeToPremium: "Actualizar a Premium",
    premiumFeaturesInclude: "Las Funciones Premium Incluyen:",
    customTimerLengths: "Duraciones de temporizador personalizadas (sesiones de trabajo profundo de 90/15 min)",
    productivityBasedThemes: "Temas adaptativos basados en productividad",
    premiumNotifications: "Notificaciones de sonido premium",
    xpBonusFeature: "20% de bonificación XP en todas las actividades",
    advancedAnalytics: "Análisis avanzados y perspectivas",
    premiumMonthly: "Premium Mensual",
    subscribeNow: "Suscribirse Ahora",
    processing: "Procesando...",
    premiumNote: "✨ ¡Comienza tu viaje premium hoy y desbloquea tu potencial de productividad completo!",
    
    // Custom Timer Modal
    editTimer: "Editar Temporizador",
    createCustomTimer: "Crear Temporizador Personalizado",
    timerName: "Nombre del Temporizador",
    timerNamePlaceholder: "ej., Sesión de Trabajo Profundo",
    focusTimeMin: "Tiempo de Enfoque (minutos)",
    shortBreakMin: "Descanso Corto (minutos)",
    longBreakMin: "Descanso Largo (minutos)",
    cancel: "Cancelar",
    updateTimer: "Actualizar Temporizador",
    createTimerBtn: "Crear Temporizador",
    
    // Payment Success
    processingPayment: "Procesando tu pago...",
    pleaseWait: "Por favor espera mientras confirmamos tu suscripción.",
    welcomeToPremium: "¡Bienvenido a Premium!",
    subscriptionActivated: "Tu suscripción ha sido activada exitosamente.",
    amount: "Cantidad",
    date: "Fecha",
    continueToApp: "Continuar a la App",
    paymentFailed: "Pago Falló",
    paymentIssue: "Hubo un problema procesando tu pago. Por favor intenta de nuevo.",
    backToApp: "Volver a la App",
    paymentTimeout: "Tiempo de Verificación de Pago Agotado",
    stillProcessing: "Aún estamos procesando tu pago. Por favor revisa tu email para confirmación.",
    somethingWrong: "Algo Salió Mal",
    contactSupport: "Encontramos un error verificando tu estado de pago. Por favor contacta soporte.",
    
    // Common
    loading: "Cargando...",
    loadingApp: "Cargando FocusFlow...",
    delete: "Eliminar",
    edit: "Editar",
    save: "Guardar",
    close: "Cerrar"
  },
  fr: {
    // Navigation
    dashboard: "Tableau de Bord",
    tasks: "Tâches",
    focus: "Focus",
    
    // Dashboard
    welcomeBack: "Bon retour",
    todayTheme: "Thème d'Aujourd'hui",
    productivityTheme: "Thème de Productivité",
    level: "Niveau",
    xpToNext: "XP pour Niveau",
    todayTasks: "Tâches d'Aujourd'hui",
    focusSessions: "Sessions de Focus",
    focusTime: "Temps de Focus",
    currentStreak: "Série Actuelle",
    days: "jours",
    yourPlan: "Votre Plan",
    recentAchievements: "Réalisations Récentes",
    
    // Premium Features
    customTimers: "Minuteries Personnalisées",
    adaptiveThemes: "Thèmes Adaptatifs",
    premiumSounds: "Sons Premium",
    xpBonus: "Bonus XP",
    enabled: "Activé",
    premiumOnly: "Premium seulement",
    standardXp: "XP Standard",
    upgradeToPremium: "Passer à Premium - Débloquez toutes les fonctionnalités pour 9,99€/mois",
    
    // Tasks
    whatTodo: "Que faut-il faire?",
    addDescription: "Ajouter une description (optionnel)",
    addTask: "Ajouter Tâche",
    addTaskXp: "Ajouter Tâche (+{xp} XP)",
    premiumBonus: "Bonus 20%!",
    pendingTasks: "Tâches en Attente",
    completedTasks: "Tâches Terminées",
    moreTasks: "+{count} tâches terminées de plus",
    noTasksYet: "Aucune tâche pour le moment!",
    createFirstTask: "Créez votre première tâche pour commencer votre parcours de productivité.",
    
    // Timer
    focusTime: "Temps de Focus",
    shortBreak: "Pause Courte",
    longBreak: "Pause Longue",
    paused: "En Pause",
    start: "Démarrer",
    resume: "Reprendre",
    pause: "Pause",
    reset: "Réinitialiser",
    
    // Custom Timers
    customTimersTitle: "Minuteries Personnalisées",
    createTimer: "Créer Minuterie",
    useTimer: "Utiliser",
    deleteTimer: "Supprimer",
    usingTimer: "Utilisant",
    useDefaultTimer: "Utiliser Minuterie Par Défaut",
    
    // Premium Upsell
    wantCustomTimers: "Voulez des Durées de Minuterie Personnalisées?",
    unlockFeatures: "Débloquez les sessions de travail profond 90/15, les thèmes de productivité et 20% de bonus XP avec Premium!",
    upgradeBtn: "Passer à Premium - 9,99€/mois",
    
    // Subscription Modal
    upgradeToPremium: "Passer à Premium",
    premiumFeaturesInclude: "Les Fonctionnalités Premium Incluent:",
    customTimerLengths: "Durées de minuterie personnalisées (sessions de travail profond 90/15 min)",
    productivityBasedThemes: "Thèmes adaptatifs basés sur la productivité",
    premiumNotifications: "Notifications sonores premium",
    xpBonusFeature: "20% de bonus XP sur toutes les activités",
    advancedAnalytics: "Analyses avancées et insights",
    premiumMonthly: "Premium Mensuel",
    subscribeNow: "S'abonner Maintenant",
    processing: "Traitement en cours...",
    premiumNote: "✨ Commencez votre voyage premium aujourd'hui et débloquez votre plein potentiel de productivité!",
    
    // Custom Timer Modal
    editTimer: "Modifier Minuterie",
    createCustomTimer: "Créer Minuterie Personnalisée",
    timerName: "Nom de la Minuterie",
    timerNamePlaceholder: "ex., Session de Travail Profond",
    focusTimeMin: "Temps de Focus (minutes)",
    shortBreakMin: "Pause Courte (minutes)",
    longBreakMin: "Pause Longue (minutes)",
    cancel: "Annuler",
    updateTimer: "Mettre à Jour Minuterie",
    createTimerBtn: "Créer Minuterie",
    
    // Payment Success
    processingPayment: "Traitement de votre paiement...",
    pleaseWait: "Veuillez patienter pendant que nous confirmons votre abonnement.",
    welcomeToPremium: "Bienvenue dans Premium!",
    subscriptionActivated: "Votre abonnement a été activé avec succès.",
    amount: "Montant",
    date: "Date",
    continueToApp: "Continuer vers l'App",
    paymentFailed: "Échec du Paiement",
    paymentIssue: "Il y a eu un problème lors du traitement de votre paiement. Veuillez réessayer.",
    backToApp: "Retour à l'App",
    paymentTimeout: "Délai de Vérification du Paiement Dépassé",
    stillProcessing: "Nous traitons encore votre paiement. Veuillez vérifier votre email pour confirmation.",
    somethingWrong: "Quelque Chose a Mal Tourné",
    contactSupport: "Nous avons rencontré une erreur lors de la vérification de votre statut de paiement. Veuillez contacter le support.",
    
    // Common
    loading: "Chargement...",
    loadingApp: "Chargement de FocusFlow...",
    delete: "Supprimer",
    edit: "Modifier",
    save: "Sauvegarder",
    close: "Fermer"
  },
  de: {
    // Navigation
    dashboard: "Dashboard",
    tasks: "Aufgaben",
    focus: "Fokus",
    
    // Dashboard
    welcomeBack: "Willkommen zurück",
    todayTheme: "Heutiges Thema",
    productivityTheme: "Produktivitäts-Thema",
    level: "Level",
    xpToNext: "XP bis Level",
    todayTasks: "Heutige Aufgaben",
    focusSessions: "Fokus-Sitzungen",
    focusTime: "Fokus-Zeit",
    currentStreak: "Aktuelle Serie",
    days: "Tage",
    yourPlan: "Ihr Plan",
    recentAchievements: "Neueste Erfolge",
    
    // Premium Features
    customTimers: "Benutzerdefinierte Timer",
    adaptiveThemes: "Adaptive Designs",
    premiumSounds: "Premium-Klänge",
    xpBonus: "XP-Bonus",
    enabled: "Aktiviert",
    premiumOnly: "Nur Premium",
    standardXp: "Standard XP",
    upgradeToPremium: "Auf Premium upgraden - Alle Funktionen für 9,99€/Monat freischalten",
    
    // Tasks
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
    
    // Timer
    focusTime: "Fokus-Zeit",
    shortBreak: "Kurze Pause",
    longBreak: "Lange Pause",
    paused: "Pausiert",
    start: "Starten",
    resume: "Fortsetzen",
    pause: "Pause",
    reset: "Zurücksetzen",
    
    // Custom Timers
    customTimersTitle: "Benutzerdefinierte Timer",
    createTimer: "Timer erstellen",
    useTimer: "Verwenden",
    deleteTimer: "Löschen",
    usingTimer: "Verwende",
    useDefaultTimer: "Standard-Timer verwenden",
    
    // Premium Upsell
    wantCustomTimers: "Möchten Sie benutzerdefinierte Timer-Längen?",
    unlockFeatures: "Schalten Sie 90/15 Deep-Work-Sitzungen, Produktivitäts-Designs und 20% XP-Bonus mit Premium frei!",
    upgradeBtn: "Auf Premium upgraden - 9,99€/Monat",
    
    // Subscription Modal
    upgradeToPremium: "Auf Premium upgraden",
    premiumFeaturesInclude: "Premium-Funktionen umfassen:",
    customTimerLengths: "Benutzerdefinierte Timer-Längen (90/15 Min Deep-Work-Sitzungen)",
    productivityBasedThemes: "Produktivitätsbasierte adaptive Designs",
    premiumNotifications: "Premium-Klang-Benachrichtigungen",
    xpBonusFeature: "20% XP-Bonus bei allen Aktivitäten",
    advancedAnalytics: "Erweiterte Analysen und Einblicke",
    premiumMonthly: "Premium Monatlich",
    subscribeNow: "Jetzt abonnieren",
    processing: "Wird verarbeitet...",
    premiumNote: "✨ Starten Sie noch heute Ihre Premium-Reise und entfesseln Sie Ihr volles Produktivitätspotential!",
    
    // Custom Timer Modal
    editTimer: "Timer bearbeiten",
    createCustomTimer: "Benutzerdefinierten Timer erstellen",
    timerName: "Timer-Name",
    timerNamePlaceholder: "z.B. Deep-Work-Sitzung",
    focusTimeMin: "Fokus-Zeit (Minuten)",
    shortBreakMin: "Kurze Pause (Minuten)",
    longBreakMin: "Lange Pause (Minuten)",
    cancel: "Abbrechen",
    updateTimer: "Timer aktualisieren",
    createTimerBtn: "Timer erstellen",
    
    // Payment Success
    processingPayment: "Ihre Zahlung wird verarbeitet...",
    pleaseWait: "Bitte warten Sie, während wir Ihr Abonnement bestätigen.",
    welcomeToPremium: "Willkommen bei Premium!",
    subscriptionActivated: "Ihr Abonnement wurde erfolgreich aktiviert.",
    amount: "Betrag",
    date: "Datum",
    continueToApp: "Zur App fortfahren",
    paymentFailed: "Zahlung fehlgeschlagen",
    paymentIssue: "Es gab ein Problem bei der Verarbeitung Ihrer Zahlung. Bitte versuchen Sie es erneut.",
    backToApp: "Zurück zur App",
    paymentTimeout: "Zahlungsstatus-Überprüfung abgelaufen",
    stillProcessing: "Wir verarbeiten Ihre Zahlung noch. Bitte überprüfen Sie Ihre E-Mail zur Bestätigung.",
    somethingWrong: "Etwas ist schiefgelaufen",
    contactSupport: "Wir haben einen Fehler bei der Überprüfung Ihres Zahlungsstatus festgestellt. Bitte kontaktieren Sie den Support.",
    
    // Common
    loading: "Laden...",
    loadingApp: "FocusFlow wird geladen...",
    delete: "Löschen",
    edit: "Bearbeiten",
    save: "Speichern",
    close: "Schließen"
  }
};

// Context for user and app state
const AppContext = createContext();

const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

// Language Context
const LanguageContext = createContext();

const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    const savedLang = localStorage.getItem('focusflow-language');
    return savedLang || 'en';
  });

  const changeLanguage = (newLang) => {
    setLanguage(newLang);
    localStorage.setItem('focusflow-language', newLang);
  };

  const t = (key, params = {}) => {
    const keys = key.split('.');
    let value = translations[language];
    
    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k];
      } else {
        break;
      }
    }
    
    if (typeof value === 'string') {
      // Replace parameters like {xp}, {count}
      return value.replace(/\{(\w+)\}/g, (match, param) => {
        return params[param] !== undefined ? params[param] : match;
      });
    }
    
    return key; // Return key if translation not found
  };

  return (
    <LanguageContext.Provider value={{ language, changeLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

// Language Switcher Component
const LanguageSwitcher = () => {
  const { language, changeLanguage, t } = useLanguage();

  const languages = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' }
  ];

  return (
    <div className="language-switcher">
      <select 
        value={language} 
        onChange={(e) => changeLanguage(e.target.value)}
        className="language-select"
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.flag} {lang.name}
          </option>
        ))}
      </select>
    </div>
  );
};

// Top Referral Banner Component  
const TopReferralBanner = ({ currentView, setCurrentView }) => {
  const { user } = useAppContext();
  const { t } = useLanguage();
  const [referralStats, setReferralStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      fetchReferralData();
    }
  }, [user]);

  const fetchReferralData = async () => {
    try {
      const response = await axios.get(`${API}/users/${user.id}/referral-stats`);
      setReferralStats(response.data);
    } catch (error) {
      console.error('Error fetching referral data:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyReferralLink = () => {
    if (referralStats?.referral_link) {
      navigator.clipboard.writeText(referralStats.referral_link);
      alert('Referral link copied to clipboard!');
    }
  };

  if (loading || !referralStats) {
    return null;
  }

  return (
    <div className="top-banner-referral">
      <div className="banner-content">
        <div className="banner-left">
          <div className="earnings-display">
            <span className="earnings-icon">💰</span>
            <span className="earnings-text">
              <strong>${referralStats.total_commission_earned.toFixed(2)}</strong> earned
            </span>
            <span className="divider">|</span>
            <span className="available-text">
              ${referralStats.available_balance.toFixed(2)} available
            </span>
          </div>
        </div>
        
        <div className="banner-center">
          <span className="banner-message">
            Earn <strong>$5</strong> per Premium referral! Share: <strong>{referralStats.referral_code}</strong>
          </span>
        </div>
        
        <div className="banner-right">
          <LanguageSwitcher />
          <button className="copy-link-btn" onClick={copyReferralLink}>
            Copy Link
          </button>
          <button 
            className="view-referrals-btn"
            onClick={() => setCurrentView('referrals')}
          >
            View Details
          </button>
        </div>
      </div>
    </div>
  );
};

// Referral Dashboard Component
const ReferralDashboard = () => {
  const { user } = useAppContext();
  const { t } = useLanguage();
  const [referralStats, setReferralStats] = useState(null);
  const [referralHistory, setReferralHistory] = useState([]);
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);

  useEffect(() => {
    if (user) {
      fetchReferralData();
    }
  }, [user]);

  const fetchReferralData = async () => {
    try {
      setLoading(true);
      const [statsResponse, historyResponse, withdrawalResponse] = await Promise.all([
        axios.get(`${API}/users/${user.id}/referral-stats`),
        axios.get(`${API}/users/${user.id}/referrals?limit=10`),
        axios.get(`${API}/users/${user.id}/withdrawals`)
      ]);
      
      setReferralStats(statsResponse.data);
      setReferralHistory(historyResponse.data);
      setWithdrawals(withdrawalResponse.data);
    } catch (error) {
      console.error('Error fetching referral data:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyReferralLink = () => {
    if (referralStats?.referral_link) {
      navigator.clipboard.writeText(referralStats.referral_link);
      // Show success message
      alert('Referral link copied to clipboard!');
    }
  };

  const requestWithdrawal = async () => {
    try {
      const response = await axios.post(`${API}/users/${user.id}/withdraw`, {
        method: "bank_transfer"
      });
      
      if (response.data.amount > 0) {
        alert(`Withdrawal request submitted for $${response.data.amount}!`);
        fetchReferralData(); // Refresh data
        setShowWithdrawModal(false);
      }
    } catch (error) {
      console.error('Error requesting withdrawal:', error);
      alert('Error processing withdrawal request');
    }
  };

  if (loading) {
    return <div className="loading">{t('loading')}</div>;
  }

  if (!referralStats) {
    return <div className="error">Failed to load referral data</div>;
  }

  return (
    <div className="referral-dashboard">
      <div className="referral-header">
        <h2 className="referral-title">💰 Earn $5 Per Referral</h2>
        <p className="referral-subtitle">Share FocusFlow and earn money for each Premium signup!</p>
      </div>

      {/* Earnings Overview */}
      <div className="earnings-overview">
        <div className="earnings-card total">
          <div className="earnings-icon">💳</div>
          <div className="earnings-content">
            <div className="earnings-amount">${referralStats.total_commission_earned.toFixed(2)}</div>
            <div className="earnings-label">Total Earned</div>
          </div>
        </div>

        <div className="earnings-card available">
          <div className="earnings-icon">💰</div>
          <div className="earnings-content">
            <div className="earnings-amount">${referralStats.available_for_withdrawal.toFixed(2)}</div>
            <div className="earnings-label">Available Now</div>
          </div>
        </div>

        <div className="earnings-card referrals">
          <div className="earnings-icon">👥</div>
          <div className="earnings-content">
            <div className="earnings-amount">{referralStats.total_referrals}</div>
            <div className="earnings-label">Total Referrals</div>
          </div>
        </div>

        <div className="earnings-card potential">
          <div className="earnings-icon">🎯</div>
          <div className="earnings-content">
            <div className="earnings-amount">${referralStats.earnings_breakdown.total_possible.toFixed(2)}</div>
            <div className="earnings-label">Potential Earnings</div>
          </div>
        </div>
      </div>

      {/* Instant Withdrawal Button */}
      {referralStats.available_for_withdrawal > 0 && (
        <div className="withdrawal-section">
          <div className="withdrawal-card">
            <div className="withdrawal-content">
              <h3>💸 ${referralStats.available_for_withdrawal.toFixed(2)} Ready to Withdraw!</h3>
              <p>Your commission is ready for instant withdrawal to your bank account.</p>
              <button 
                className="withdraw-btn instant"
                onClick={() => setShowWithdrawModal(true)}
              >
                Withdraw ${referralStats.available_for_withdrawal.toFixed(2)} Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Referral Link Sharing */}
      <div className="referral-sharing">
        <h3>🔗 Your Referral Link</h3>
        <div className="referral-link-card">
          <div className="referral-code-display">
            <span className="referral-code">{referralStats.referral_code}</span>
            <span className="referral-commission">+$5.00</span>
          </div>
          <div className="referral-link-container">
            <input 
              type="text" 
              value={referralStats.referral_link} 
              readOnly 
              className="referral-link-input"
            />
            <button className="copy-link-btn" onClick={copyReferralLink}>
              📋 Copy Link
            </button>
          </div>
          <p className="referral-instruction">
            Share this link with friends. When they subscribe to Premium, you instantly earn $5!
          </p>
        </div>
      </div>

      {/* Social Sharing Buttons */}
      <div className="social-sharing">
        <h3>📢 Share & Earn</h3>
        <div className="share-buttons">
          <button 
            className="share-btn twitter"
            onClick={() => window.open(`https://twitter.com/intent/tweet?text=Check out FocusFlow, the best productivity app! Use my link to get started: ${encodeURIComponent(referralStats.referral_link)}`, '_blank')}
          >
            🐦 Twitter
          </button>
          <button 
            className="share-btn facebook"
            onClick={() => window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(referralStats.referral_link)}`, '_blank')}
          >
            📘 Facebook
          </button>
          <button 
            className="share-btn instagram"
            onClick={() => {
              navigator.clipboard.writeText(`Check out FocusFlow! 🚀 The ultimate productivity app with Pomodoro timers and gamification. Use my referral link: ${referralStats.referral_link} #FocusFlow #Productivity #PomodoroTimer`);
              alert('Instagram post text copied! Paste it in your Instagram story or post 📱');
            }}
          >
            📸 Instagram
          </button>
          <button 
            className="share-btn tiktok"
            onClick={() => {
              navigator.clipboard.writeText(`Boost your productivity with FocusFlow! 🎯 Pomodoro timer + gamification + earnings! My referral link: ${referralStats.referral_link} #ProductivityHacks #FocusFlow #PomodoroMethod #StudyTips`);
              alert('TikTok caption copied! Use it for your productivity video 🎥');
            }}
          >
            🎵 TikTok
          </button>
          <button 
            className="share-btn linkedin"
            onClick={() => window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(referralStats.referral_link)}`, '_blank')}
          >
            💼 LinkedIn
          </button>
          <button 
            className="share-btn whatsapp"
            onClick={() => window.open(`https://wa.me/?text=Check out FocusFlow! ${encodeURIComponent(referralStats.referral_link)}`, '_blank')}
          >
            💬 WhatsApp
          </button>
        </div>
      </div>

      {/* Referral History */}
      {referralHistory.length > 0 && (
        <div className="referral-history">
          <h3>📊 Recent Referrals</h3>
          <div className="referral-list">
            {referralHistory.map((referral, index) => (
              <div key={referral.id || index} className={`referral-item ${referral.status}`}>
                <div className="referral-info">
                  <div className="referral-status">
                    {referral.status === 'completed' ? '✅' : '⏳'}
                  </div>
                  <div className="referral-details">
                    <div className="referral-date">
                      {new Date(referral.created_at).toLocaleDateString()}
                    </div>
                    <div className="referral-amount">
                      ${referral.commission_earned.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="referral-status-text">
                  {referral.status === 'completed' ? 'Earned' : 'Pending'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* How It Works */}
      <div className="how-it-works">
        <h3>❓ How It Works</h3>
        <div className="steps">
          <div className="step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h4>Share Your Link</h4>
              <p>Copy and share your unique referral link with friends</p>
            </div>
          </div>
          <div className="step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h4>Friend Subscribes</h4>
              <p>When they upgrade to Premium ($9.99/month)</p>
            </div>
          </div>
          <div className="step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h4>You Get $5 Instantly</h4>
              <p>Commission is credited immediately and ready to withdraw</p>
            </div>
          </div>
        </div>
      </div>

      {/* Withdrawal Modal */}
      {showWithdrawModal && (
        <div className="modal-overlay">
          <div className="modal-content withdrawal-modal">
            <div className="modal-header">
              <h3>💸 Withdraw Earnings</h3>
              <button className="modal-close" onClick={() => setShowWithdrawModal(false)}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="withdrawal-summary">
                <div className="withdrawal-amount">
                  ${referralStats.available_for_withdrawal.toFixed(2)}
                </div>
                <p>Available for withdrawal to your bank account</p>
              </div>
              
              <div className="withdrawal-info">
                <p><strong>Processing Time:</strong> 3-5 business days</p>
                <p><strong>Fees:</strong> Free withdrawals</p>
                <p><strong>Method:</strong> Bank Transfer</p>
              </div>
            </div>
            
            <div className="modal-footer">
              <button className="modal-btn secondary" onClick={() => setShowWithdrawModal(false)}>
                Cancel
              </button>
              <button className="modal-btn primary" onClick={requestWithdrawal}>
                Confirm Withdrawal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
const Timer = ({ onComplete, isActive, timeLeft, totalTime }) => {
  const { t } = useLanguage();
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
          <div className="timer-status">{isActive ? t('focusTime') : t('paused')}</div>
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

const CustomTimerModal = ({ isOpen, onClose, onSave, editingTimer }) => {
  const [name, setName] = useState('');
  const [focusMinutes, setFocusMinutes] = useState(25);
  const [shortBreakMinutes, setShortBreakMinutes] = useState(5);
  const [longBreakMinutes, setLongBreakMinutes] = useState(15);

  useEffect(() => {
    if (editingTimer) {
      setName(editingTimer.name);
      setFocusMinutes(editingTimer.focus_minutes);
      setShortBreakMinutes(editingTimer.short_break_minutes);
      setLongBreakMinutes(editingTimer.long_break_minutes);
    } else {
      setName('');
      setFocusMinutes(25);
      setShortBreakMinutes(5);
      setLongBreakMinutes(15);
    }
  }, [editingTimer]);

  const handleSave = () => {
    if (!name.trim()) return;
    
    onSave({
      name: name.trim(),
      focus_minutes: focusMinutes,
      short_break_minutes: shortBreakMinutes,
      long_break_minutes: longBreakMinutes
    });
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>{editingTimer ? 'Edit Timer' : 'Create Custom Timer'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="form-group">
            <label>Timer Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Deep Work Session"
              className="modal-input"
            />
          </div>
          
          <div className="timer-settings-grid">
            <div className="form-group">
              <label>Focus Time (minutes)</label>
              <input
                type="number"
                min="1"
                max="180"
                value={focusMinutes}
                onChange={(e) => setFocusMinutes(parseInt(e.target.value))}
                className="modal-input"
              />
            </div>
            
            <div className="form-group">
              <label>Short Break (minutes)</label>
              <input
                type="number"
                min="1"
                max="60"
                value={shortBreakMinutes}
                onChange={(e) => setShortBreakMinutes(parseInt(e.target.value))}
                className="modal-input"
              />
            </div>
            
            <div className="form-group">
              <label>Long Break (minutes)</label>
              <input
                type="number"
                min="1"
                max="120"
                value={longBreakMinutes}
                onChange={(e) => setLongBreakMinutes(parseInt(e.target.value))}
                className="modal-input"
              />
            </div>
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="modal-btn secondary" onClick={onClose}>Cancel</button>
          <button className="modal-btn primary" onClick={handleSave}>
            {editingTimer ? 'Update' : 'Create'} Timer
          </button>
        </div>
      </div>
    </div>
  );
};

const SubscriptionModal = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [packages, setPackages] = useState({});

  useEffect(() => {
    if (isOpen) {
      fetchPackages();
    }
  }, [isOpen]);

  const fetchPackages = async () => {
    try {
      const response = await axios.get(`${API}/subscription/packages`);
      setPackages(response.data);
    } catch (error) {
      console.error('Error fetching packages:', error);
    }
  };

  const handleSubscribe = async (packageId) => {
    setLoading(true);
    try {
      const originUrl = window.location.origin;
      const response = await axios.post(`${API}/subscription/checkout`, {
        package_id: packageId,
        origin_url: originUrl
      });

      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url;
      }
    } catch (error) {
      console.error('Error creating checkout:', error);
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content subscription-modal">
        <div className="modal-header">
          <h3>Upgrade to Premium</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="subscription-features">
            <h4>Premium Features Include:</h4>
            <ul className="features-list">
              <li>
                <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Custom timer lengths (90/15 min deep work sessions)
              </li>
              <li>
                <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Productivity-based adaptive themes
              </li>
              <li>
                <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Premium sound notifications
              </li>
              <li>
                <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                20% XP bonus on all activities
              </li>
              <li>
                <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Advanced analytics and insights
              </li>
            </ul>
          </div>
          
          <div className="subscription-packages">
            {Object.entries(packages).map(([packageId, pkg]) => (
              <div key={packageId} className="package-card premium-package">
                <div className="package-header">
                  <h4>{pkg.name}</h4>
                  <div className="package-price">
                    <span className="price">${pkg.amount}</span>
                    <span className="period">/month</span>
                  </div>
                </div>
                <p className="package-description">{pkg.description}</p>
                <button
                  className="package-btn premium"
                  onClick={() => handleSubscribe(packageId)}
                  disabled={loading}
                >
                  {loading ? 'Processing...' : 'Subscribe Now'}
                </button>
              </div>
            ))}
          </div>
          
          <div className="subscription-note">
            <p>✨ Start your premium journey today and unlock your full productivity potential!</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const PomodoroSession = () => {
  const { user, updateUserStats } = useAppContext();
  const { t } = useLanguage();
  const [isActive, setIsActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(25 * 60); // 25 minutes in seconds
  const [sessionType, setSessionType] = useState('focus');
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [customTimers, setCustomTimers] = useState([]);
  const [selectedCustomTimer, setSelectedCustomTimer] = useState(null);
  const [showCustomTimerModal, setShowCustomTimerModal] = useState(false);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);

  const sessionTypes = {
    focus: { duration: 25 * 60, label: t('focusTime'), next: 'short_break' },
    short_break: { duration: 5 * 60, label: t('shortBreak'), next: 'focus' },
    long_break: { duration: 15 * 60, label: t('longBreak'), next: 'focus' }
  };

  useEffect(() => {
    if (user?.subscription_tier === 'premium') {
      fetchCustomTimers();
    }
  }, [user]);

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

  const fetchCustomTimers = async () => {
    try {
      const response = await axios.get(`${API}/users/${user.id}/custom-timers`);
      setCustomTimers(response.data);
    } catch (error) {
      console.error('Error fetching custom timers:', error);
    }
  };

  const createCustomTimer = async (timerData) => {
    try {
      const response = await axios.post(`${API}/users/${user.id}/custom-timers`, timerData);
      setCustomTimers([...customTimers, response.data]);
      setShowCustomTimerModal(false);
    } catch (error) {
      console.error('Error creating custom timer:', error);
      if (error.response?.status === 403) {
        setShowSubscriptionModal(true);
      }
    }
  };

  const deleteCustomTimer = async (timerId) => {
    try {
      await axios.delete(`${API}/users/${user.id}/custom-timers/${timerId}`);
      setCustomTimers(customTimers.filter(t => t.id !== timerId));
    } catch (error) {
      console.error('Error deleting custom timer:', error);
    }
  };

  const applyCustomTimer = (timer) => {
    setSelectedCustomTimer(timer);
    const newSessionTypes = {
      focus: { duration: timer.focus_minutes * 60, label: 'Focus Time', next: 'short_break' },
      short_break: { duration: timer.short_break_minutes * 60, label: 'Short Break', next: 'focus' },
      long_break: { duration: timer.long_break_minutes * 60, label: 'Long Break', next: 'focus' }
    };
    
    // Update current session
    setSessionType('focus');
    setTimeLeft(newSessionTypes.focus.duration);
    setIsActive(false);
    setCurrentSessionId(null);
  };

  const resetToDefault = () => {
    setSelectedCustomTimer(null);
    setSessionType('focus');
    setTimeLeft(25 * 60);
    setIsActive(false);
    setCurrentSessionId(null);
  };

  const getCurrentDuration = () => {
    if (selectedCustomTimer) {
      const durations = {
        focus: selectedCustomTimer.focus_minutes * 60,
        short_break: selectedCustomTimer.short_break_minutes * 60,
        long_break: selectedCustomTimer.long_break_minutes * 60
      };
      return durations[sessionType];
    }
    return sessionTypes[sessionType].duration;
  };

  const startTimer = async () => {
    if (!currentSessionId) {
      try {
        const response = await axios.post(`${API}/users/${user.id}/focus-sessions`, {
          timer_type: sessionType,
          duration_minutes: getCurrentDuration() / 60
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
    setTimeLeft(getCurrentDuration());
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
    const nextDuration = selectedCustomTimer ? 
      (nextType === 'focus' ? selectedCustomTimer.focus_minutes : 
       nextType === 'short_break' ? selectedCustomTimer.short_break_minutes : 
       selectedCustomTimer.long_break_minutes) * 60 :
      sessionTypes[nextType].duration;
    setTimeLeft(nextDuration);
    setCurrentSessionId(null);
  };

  return (
    <div className="pomodoro-container">
      {selectedCustomTimer && (
        <div className="custom-timer-info">
          <div className="timer-name">Using: {selectedCustomTimer.name}</div>
          <button className="reset-timer-btn" onClick={resetToDefault}>
            Use Default Timer
          </button>
        </div>
      )}

      <div className="session-type-selector">
        {Object.entries(sessionTypes).map(([type, config]) => (
          <button
            key={type}
            className={`session-type-btn ${sessionType === type ? 'active' : ''}`}
            onClick={() => {
              setSessionType(type);
              setTimeLeft(getCurrentDuration());
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
        totalTime={getCurrentDuration()}
        onComplete={handleSessionComplete}
      />

      <div className="timer-controls">
        {!isActive ? (
          <button className="timer-btn primary" onClick={startTimer}>
            {timeLeft === getCurrentDuration() ? 'Start' : 'Resume'}
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

      {/* Premium Custom Timers Section */}
      {user?.subscription_tier === 'premium' && (
        <div className="premium-timers-section">
          <div className="section-header">
            <h4>Custom Timers</h4>
            <button
              className="create-timer-btn"
              onClick={() => setShowCustomTimerModal(true)}
            >
              + Create Timer
            </button>
          </div>
          
          {customTimers.length > 0 && (
            <div className="custom-timers-list">
              {customTimers.map(timer => (
                <div key={timer.id} className="custom-timer-card">
                  <div className="timer-info">
                    <h5>{timer.name}</h5>
                    <p>{timer.focus_minutes}/{timer.short_break_minutes}/{timer.long_break_minutes} min</p>
                  </div>
                  <div className="timer-actions">
                    <button
                      className="apply-timer-btn"
                      onClick={() => applyCustomTimer(timer)}
                    >
                      Use
                    </button>
                    <button
                      className="delete-timer-btn"
                      onClick={() => deleteCustomTimer(timer.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Free User Upgrade Prompt */}
      {user?.subscription_tier === 'free' && (
        <div className="premium-upsell">
          <div className="upsell-content">
            <h4>Want Custom Timer Lengths?</h4>
            <p>Unlock 90/15 deep work sessions, productivity themes, and 20% XP bonus with Premium!</p>
            <button
              className="upgrade-btn"
              onClick={() => setShowSubscriptionModal(true)}
            >
              Upgrade to Premium - $9.99/month
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      <CustomTimerModal
        isOpen={showCustomTimerModal}
        onClose={() => setShowCustomTimerModal(false)}
        onSave={createCustomTimer}
      />

      <SubscriptionModal
        isOpen={showSubscriptionModal}
        onClose={() => setShowSubscriptionModal(false)}
      />
    </div>
  );
};

const SubscriptionSuccessHandler = () => {
  const { updateUserStats } = useAppContext();
  const [status, setStatus] = useState('checking');
  const [paymentDetails, setPaymentDetails] = useState(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (sessionId) {
      checkPaymentStatus(sessionId);
    }
  }, []);

  const checkPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 10;
    const pollInterval = 2000; // 2 seconds

    if (attempts >= maxAttempts) {
      setStatus('timeout');
      return;
    }

    try {
      const response = await axios.get(`${API}/subscription/status/${sessionId}`);
      const data = response.data;
      
      if (data.payment_status === 'completed') {
        setStatus('success');
        setPaymentDetails(data);
        updateUserStats(); // Refresh user data to show premium status
        return;
      } else if (data.payment_status === 'failed' || data.payment_status === 'expired') {
        setStatus('failed');
        return;
      }

      // Continue polling
      setTimeout(() => checkPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      if (attempts < 3) {
        setTimeout(() => checkPaymentStatus(sessionId, attempts + 1), pollInterval);
      } else {
        setStatus('error');
      }
    }
  };

  const getStatusDisplay = () => {
    switch (status) {
      case 'checking':
        return (
          <div className="payment-status checking">
            <div className="status-spinner"></div>
            <h3>Processing your payment...</h3>
            <p>Please wait while we confirm your subscription.</p>
          </div>
        );
      
      case 'success':
        return (
          <div className="payment-status success">
            <div className="status-icon success">✅</div>
            <h3>Welcome to Premium!</h3>
            <p>Your subscription has been activated successfully.</p>
            <div className="payment-details">
              {paymentDetails && (
                <>
                  <p>Amount: ${paymentDetails.amount} {paymentDetails.currency.toUpperCase()}</p>
                  <p>Date: {new Date(paymentDetails.completed_at).toLocaleDateString()}</p>
                </>
              )}
            </div>
            <button
              className="continue-btn"
              onClick={() => window.location.href = '/'}
            >
              Continue to App
            </button>
          </div>
        );
      
      case 'failed':
        return (
          <div className="payment-status failed">
            <div className="status-icon failed">❌</div>
            <h3>Payment Failed</h3>
            <p>There was an issue processing your payment. Please try again.</p>
            <button
              className="retry-btn"
              onClick={() => window.location.href = '/'}
            >
              Back to App
            </button>
          </div>
        );
      
      case 'timeout':
        return (
          <div className="payment-status timeout">
            <div className="status-icon timeout">⏰</div>
            <h3>Payment Status Check Timed Out</h3>
            <p>We're still processing your payment. Please check your email for confirmation.</p>
            <button
              className="continue-btn"
              onClick={() => window.location.href = '/'}
            >
              Back to App
            </button>
          </div>
        );
      
      default:
        return (
          <div className="payment-status error">
            <div className="status-icon error">⚠️</div>
            <h3>Something Went Wrong</h3>
            <p>We encountered an error checking your payment status. Please contact support.</p>
            <button
              className="continue-btn"
              onClick={() => window.location.href = '/'}
            >
              Back to App
            </button>
          </div>
        );
    }
  };

  return (
    <div className="subscription-success-page">
      <div className="status-container">
        {getStatusDisplay()}
      </div>
    </div>
  );
};

const TaskManager = () => {
  const { user, tasks, setTasks, updateUserStats } = useAppContext();
  const { t } = useLanguage();
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
  const xpAmount = user?.subscription_tier === 'premium' ? '12' : '10';

  return (
    <div className="task-manager">
      <form onSubmit={addTask} className="task-form">
        <div className="form-group">
          <input
            type="text"
            value={newTaskTitle}
            onChange={(e) => setNewTaskTitle(e.target.value)}
            placeholder={t('whatTodo')}
            className="task-input"
            maxLength={100}
          />
        </div>
        <div className="form-group">
          <textarea
            value={newTaskDescription}
            onChange={(e) => setNewTaskDescription(e.target.value)}
            placeholder={t('addDescription')}
            className="task-textarea"
            rows={2}
            maxLength={200}
          />
        </div>
        <button type="submit" className="add-task-btn">
          <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          {t('addTaskXp', { xp: xpAmount })}
          {user?.subscription_tier === 'premium' && (
            <span className="premium-bonus">{t('premiumBonus')}</span>
          )}
        </button>
      </form>

      <div className="task-sections">
        {pendingTasks.length > 0 && (
          <div className="task-section">
            <h3 className="section-title">{t('pendingTasks')} ({pendingTasks.length})</h3>
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
            <h3 className="section-title">{t('completedTasks')} ({completedTasks.length})</h3>
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
                <p className="more-tasks">{t('moreTasks', { count: completedTasks.length - 5 })}</p>
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
              <h3>{t('noTasksYet')}</h3>
              <p>{t('createFirstTask')}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const SinglePageDashboard = () => {
  const { user, tasks, setTasks, dashboardData, updateUserStats } = useAppContext();
  const { t } = useLanguage();
  
  // Referral state
  const [referralStats, setReferralStats] = useState(null);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  
  // Task state
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDescription, setNewTaskDescription] = useState('');
  
  // Timer state
  const [isActive, setIsActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(25 * 60);
  const [sessionType, setSessionType] = useState('focus');
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);

  const sessionTypes = {
    focus: { duration: 25 * 60, label: t('focusTime'), next: 'short_break' },
    short_break: { duration: 5 * 60, label: t('shortBreak'), next: 'focus' },
    long_break: { duration: 15 * 60, label: t('longBreak'), next: 'focus' }
  };

  useEffect(() => {
    if (user) {
      fetchReferralData();
    }
  }, [user]);

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

  const fetchReferralData = async () => {
    try {
      const response = await axios.get(`${API}/users/${user.id}/referral-stats`);
      setReferralStats(response.data);
    } catch (error) {
      console.error('Error fetching referral data:', error);
    }
  };

  // Timer functions
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

  const pauseTimer = () => setIsActive(false);
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
    const nextType = sessionTypes[sessionType].next;
    setSessionType(nextType);
    setTimeLeft(sessionTypes[nextType].duration);
    setCurrentSessionId(null);
  };

  // Task functions
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

  const copyReferralLink = () => {
    if (referralStats?.referral_link) {
      navigator.clipboard.writeText(referralStats.referral_link);
      alert('Referral link copied to clipboard!');
    }
  };

  const requestWithdrawal = async () => {
    try {
      const response = await axios.post(`${API}/users/${user.id}/withdraw`, {
        method: "bank_transfer"
      });
      if (response.data.amount > 0) {
        alert(`Withdrawal request submitted for $${response.data.amount}!`);
        fetchReferralData();
        setShowWithdrawModal(false);
      }
    } catch (error) {
      console.error('Error requesting withdrawal:', error);
      alert('Error processing withdrawal request');
    }
  };

  if (!dashboardData || !referralStats) {
    return <div className="loading">{t('loadingApp')}</div>;
  }

  const { today_stats, level_progress, recent_achievements, premium_features, theme } = dashboardData;
  const pendingTasks = tasks.filter(t => t.status === 'pending');
  const completedTasks = tasks.filter(t => t.status === 'completed');
  const xpAmount = user?.subscription_tier === 'premium' ? '12' : '10';

  return (
    <div className="single-page-dashboard">
      {/* Header with Welcome Message */}
      <div className="dashboard-header">
        <div className="user-welcome">
          <h1 className="welcome-text">{t('welcomeBack')}, {user.name}!</h1>
          <div className={`theme-badge theme-${theme.primary}`}>
            {premium_features.productivity_themes ? 
              `${t('productivityTheme')}: ${theme.name}` : 
              `${t('todayTheme')}: ${theme.name}`}
          </div>
        </div>

        <div className="level-card-compact">
          <div className="level-info">
            <div className="level-number">Level {user.level}</div>
            <div className="level-progress">
              <div 
                className="level-progress-bar"
                style={{ width: `${level_progress.progress_percentage}%` }}
              ></div>
            </div>
          </div>
          <div className="total-xp">{user.total_xp} XP</div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="quick-stats-grid">
        <StatsCard title={t('todayTasks')} value={today_stats.tasks_completed} className="stats-card-tasks" />
        <StatsCard title={t('focusSessions')} value={today_stats.focus_sessions_completed} className="stats-card-focus" />
        <StatsCard title={t('focusTime')} value={`${today_stats.total_focus_time}m`} className="stats-card-time" />
        <StatsCard title={t('currentStreak')} value={`${user.current_streak} ${t('days')}`} className="stats-card-streak" />
      </div>

      {/* Main Content Grid */}
      <div className="main-content-grid">
        {/* Focus Timer */}
        <div className="focus-section">
          <h2 className="section-title">⏱️ {t('focus')} Timer</h2>
          
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
                {timeLeft === sessionTypes[sessionType].duration ? t('start') : t('resume')}
              </button>
            ) : (
              <button className="timer-btn secondary" onClick={pauseTimer}>
                {t('pause')}
              </button>
            )}
            <button className="timer-btn secondary" onClick={resetTimer}>
              {t('reset')}
            </button>
          </div>
        </div>

        {/* Task Management */}
        <div className="tasks-section">
          <h2 className="section-title">✅ {t('tasks')}</h2>
          
          <form onSubmit={addTask} className="task-form-compact">
            <div className="form-group">
              <input
                type="text"
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                placeholder={t('whatTodo')}
                className="task-input-compact"
                maxLength={100}
              />
            </div>
            <button type="submit" className="add-task-btn-compact">
              {t('addTaskXp', { xp: xpAmount })}
              {user?.subscription_tier === 'premium' && <span className="premium-bonus">+20%</span>}
            </button>
          </form>

          <div className="task-lists-compact">
            {pendingTasks.length > 0 && (
              <div className="task-list-compact">
                <h4>{t('pendingTasks')} ({pendingTasks.length})</h4>
                {pendingTasks.slice(0, 5).map(task => (
                  <TaskItem key={task.id} task={task} onToggle={toggleTask} onDelete={deleteTask} />
                ))}
              </div>
            )}

            {completedTasks.length > 0 && (
              <div className="task-list-compact">
                <h4>{t('completedTasks')} ({completedTasks.length})</h4>
                {completedTasks.slice(0, 3).map(task => (
                  <TaskItem key={task.id} task={task} onToggle={toggleTask} onDelete={deleteTask} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Referral Earnings */}
        <div className="referral-section">
          <h2 className="section-title">💰 Geld Verdienen</h2>
          
          <div className="earnings-summary">
            <div className="earnings-item">
              <div className="earnings-value">${referralStats.total_commission_earned.toFixed(2)}</div>
              <div className="earnings-label">Verdient</div>
            </div>
            <div className="earnings-item">
              <div className="earnings-value">{referralStats.total_referrals}</div>
              <div className="earnings-label">Empfehlungen</div>
            </div>
            <div className="earnings-item">
              <div className="earnings-value">${referralStats.available_for_withdrawal.toFixed(2)}</div>
              <div className="earnings-label">Verfügbar</div>
            </div>
          </div>

          <div className="share-buttons-compact">
            <button 
              className="share-btn-compact twitter"
              onClick={() => window.open(`https://twitter.com/intent/tweet?text=Check out FocusFlow! ${encodeURIComponent(referralStats.referral_link)}`, '_blank')}
            >
              🐦
            </button>
            <button 
              className="share-btn-compact facebook"
              onClick={() => window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(referralStats.referral_link)}`, '_blank')}
            >
              📘
            </button>
            <button 
              className="share-btn-compact instagram"
              onClick={() => {
                navigator.clipboard.writeText(`Check out FocusFlow! ${referralStats.referral_link}`);
                alert('Instagram text copied!');
              }}
            >
              📸
            </button>
            <button 
              className="share-btn-compact tiktok"
              onClick={() => {
                navigator.clipboard.writeText(`Boost your productivity with FocusFlow! ${referralStats.referral_link}`);
                alert('TikTok text copied!');
              }}
            >
              🎵
            </button>
          </div>

          <div className="referral-how-it-works">
            <p><strong>Wie es funktioniert:</strong></p>
            <ol>
              <li>Link teilen</li>
              <li>Freund kauft Premium</li>
              <li>Du bekommst sofort $5</li>
            </ol>
          </div>
        </div>

        {/* Achievements */}
        {recent_achievements.length > 0 && (
          <div className="achievements-section-compact">
            <h2 className="section-title">🏆 {t('recentAchievements')}</h2>
            {recent_achievements.slice(0, 3).map(achievement => (
              <div key={achievement.id} className="achievement-card-compact">
                <div className="achievement-icon">🏆</div>
                <div className="achievement-content">
                  <h4>{achievement.title}</h4>
                  <span className="achievement-xp">+{achievement.xp_reward} XP</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Premium Upsell */}
      {user.subscription_tier === 'free' && (
        <div className="premium-upsell-bottom">
          <div className="upsell-content">
            <h3>🚀 Premium Features freischalten</h3>
            <p>Custom Timer, Adaptive Themes, 20% XP Bonus & mehr!</p>
            <button
              className="upgrade-btn-bottom"
              onClick={() => setShowSubscriptionModal(true)}
            >
              Upgrade für $9.99/Monat
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      {showWithdrawModal && (
        <div className="modal-overlay">
          <div className="modal-content withdrawal-modal">
            <div className="modal-header">
              <h3>💸 Geld abholen</h3>
              <button className="modal-close" onClick={() => setShowWithdrawModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="withdrawal-summary">
                <div className="withdrawal-amount">${referralStats.available_for_withdrawal.toFixed(2)}</div>
                <p>Verfügbar zur Auszahlung auf dein Bankkonto</p>
              </div>
              <div className="withdrawal-info">
                <p><strong>Bearbeitungszeit:</strong> 3-5 Werktage</p>
                <p><strong>Gebühren:</strong> Kostenlos</p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="modal-btn secondary" onClick={() => setShowWithdrawModal(false)}>
                Abbrechen
              </button>
              <button className="modal-btn primary" onClick={requestWithdrawal}>
                Jetzt Auszahlen
              </button>
            </div>
          </div>
        </div>
      )}

      <SubscriptionModal
        isOpen={showSubscriptionModal}
        onClose={() => setShowSubscriptionModal(false)}
      />
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

  // Check if we're on subscription success page
  const isSubscriptionSuccess = window.location.pathname === '/subscription/success' || 
                              window.location.search.includes('session_id');

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
    <LanguageProvider>
      <AppContext.Provider value={contextValue}>
        <AppContent 
          isSubscriptionSuccess={isSubscriptionSuccess}
          currentView={currentView}
          setCurrentView={setCurrentView}
          loading={loading}
          user={user}
          theme={theme}
        />
      </AppContext.Provider>
    </LanguageProvider>
  );
};

const AppContent = ({ isSubscriptionSuccess, currentView, setCurrentView, loading, user, theme }) => {
  const { t } = useLanguage();

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>{t('loadingApp')}</p>
      </div>
    );
  }

  // Handle subscription success page
  if (isSubscriptionSuccess) {
    return (
      <div className={`app theme-${theme.primary}`}>
        <SubscriptionSuccessHandler />
      </div>
    );
  }

  return (
    <div className={`app theme-${theme.primary}`}>
      {/* Top Referral Earnings Banner */}
      <TopReferralBanner currentView={currentView} setCurrentView={setCurrentView} />
      
      <nav className="navigation">
        <div className="nav-brand">
          <h2>FocusFlow</h2>
          {user?.subscription_tier === 'premium' && (
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
            {t('dashboard')}
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
          <button
            className={`nav-item ${currentView === 'referrals' ? 'nav-item-active' : 'nav-item-inactive'}`}
            onClick={() => setCurrentView('referrals')}
          >
            <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm2 6a2 2 0 114 0 2 2 0 01-4 0zm8 0a2 2 0 114 0 2 2 0 01-4 0z" clipRule="evenodd" />
            </svg>
            💰 Referrals
          </button>
          
          <LanguageSwitcher />
        </div>
      </nav>

      <main className="main-content">
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'tasks' && <TaskManager />}
        {currentView === 'focus' && <PomodoroSession />}
        {currentView === 'referrals' && <ReferralDashboard />}
      </main>
    </div>
  );
};

export default App;