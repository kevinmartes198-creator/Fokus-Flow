from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets

# Stripe integration
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import stripe

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe initialization
stripe_api_key = os.environ.get('STRIPE_API_KEY')
if not stripe_api_key:
    raise ValueError("STRIPE_API_KEY environment variable is required")

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class TaskStatus(str, Enum):
    pending = "pending"
    completed = "completed"

class TimerType(str, Enum):
    focus = "focus"
    short_break = "short_break"
    long_break = "long_break"

class SubscriptionTier(str, Enum):
    free = "free"
    premium = "premium"  # Legacy premium (for existing users)
    premium_monthly = "premium_monthly"
    premium_yearly = "premium_yearly"  
    premium_lifetime = "premium_lifetime"

class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    expired = "expired"

class ReferralStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    paid = "paid"

class CommissionStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    paid = "paid"
    cancelled = "cancelled"

# Subscription packages with referral commissions - EUR Pricing
SUBSCRIPTION_PACKAGES = {
    "monthly_premium": {
        "amount": 9.99,
        "currency": "eur",
        "name": "Premium Monthly",
        "description": "Power-User Features: Alle Timer, Themes, XP-Boost, Cloud-Backup, Premium-Achievements",
        "duration_months": 1,
        "commission_amount": 5.00,  # €5 commission per referral
        "tier": "premium_monthly",
        "badge": "monthly_supporter"
    },
    "yearly_premium": {
        "amount": 89.99,
        "currency": "eur", 
        "name": "Premium Yearly",
        "description": "Sparfüchse & loyale Nutzer: Alle Monthly Features + 2 Monate gratis + exklusives Yearly-Badge",
        "duration_months": 12,
        "commission_amount": 15.00,  # €15 commission per yearly referral
        "tier": "premium_yearly",
        "badge": "yearly_supporter",
        "savings": "2 Monate gratis!",
        "monthly_equivalent": 7.50
    },
    "lifetime_premium": {
        "amount": 199.99,
        "currency": "eur",
        "name": "Lifetime Deal",
        "description": "Early Supporter Special: Alles für immer + exklusives Lifetime-Supporter Badge",
        "duration_months": 999,  # Effectively lifetime
        "commission_amount": 25.00,  # €25 commission per lifetime referral
        "tier": "premium_lifetime", 
        "badge": "lifetime_supporter",
        "savings": "Sonderaktion - Nur für kurze Zeit!",
        "is_special": True
    }
}

# In-App Purchase Products - Small one-time purchases (2-5€)
IN_APP_PRODUCTS = {
    "xp_booster_500": {
        "amount": 2.99,
        "currency": "eur",
        "name": "XP Booster Paket",
        "description": "Sofort +500 XP für deinen Level-Fortschritt",
        "type": "instant_reward",
        "reward": {"xp": 500},
        "category": "progression",
        "icon": "⚡"
    },
    "streak_saver": {
        "amount": 1.99,
        "currency": "eur", 
        "name": "Streak Retter",
        "description": "Schütze deinen Streak für 7 Tage - automatischer Schutz bei verpassten Tagen",
        "type": "protection",
        "reward": {"streak_protection_days": 7},
        "category": "protection",
        "icon": "🛡️"
    },
    "premium_theme_pack": {
        "amount": 3.99,
        "currency": "eur",
        "name": "Premium Theme Pack",
        "description": "Darkmode, Focus Black & Nature Set - 3 exklusive Designer-Themes",
        "type": "unlock",
        "reward": {"themes": ["darkmode", "focus_black", "nature_set"]},
        "category": "customization",
        "icon": "🎨"
    },
    "focus_powerup_pack": {
        "amount": 2.49,
        "currency": "eur",
        "name": "Focus Power-Up Pack",
        "description": "5x Turbo-Focus Booster für 1.5x XP während Sessions",
        "type": "consumable",
        "reward": {"powerups": [{"type": "focus_turbo", "count": 5, "multiplier": 1.5}]},
        "category": "enhancement",
        "icon": "🚀"
    },
    "achievement_accelerator": {
        "amount": 4.99,
        "currency": "eur",
        "name": "Achievement Accelerator",
        "description": "Schalte sofort 3 zufällige Achievements frei + Bonus XP",
        "type": "instant_unlock",
        "reward": {"instant_achievements": 3, "bonus_xp": 300},
        "category": "achievement",
        "icon": "🏆"
    },
    "custom_sound_pack": {
        "amount": 3.49,
        "currency": "eur",
        "name": "Premium Sound Pack",
        "description": "10 entspannende Fokus-Sounds: Regen, Wald, Café, Ozean & mehr",
        "type": "unlock",
        "reward": {"sounds": ["rain", "forest", "cafe", "ocean", "fireplace", "storm", "birds", "wind", "waves", "piano"]},
        "category": "audio",
        "icon": "🎵"
    }
}

# Daily Challenges - Smart engagement with micro-monetization opportunities  
DAILY_CHALLENGES = {
    "focus_master": {
        "name": "Focus Master",
        "description": "Complete 3 Pomodoro sessions today",
        "icon": "🎯",
        "goal": 3,
        "type": "focus_sessions",
        "reward": {"xp": 50, "streak_bonus": True},
        "difficulty": "easy",
        "unlock_offer": {
            "product_id": "focus_powerup_pack",
            "discount": 20,  # 20% off
            "message": "Great focus today! Get 20% off Focus Power-ups to boost tomorrow!"
        }
    },
    "task_crusher": {
        "name": "Task Crusher", 
        "description": "Complete 5 tasks in one day",
        "icon": "✅",
        "goal": 5,
        "type": "tasks_completed",
        "reward": {"xp": 75, "bonus_achievements": 1},
        "difficulty": "medium",
        "unlock_offer": {
            "product_id": "xp_booster_500", 
            "discount": 15,
            "message": "Amazing productivity! Boost your XP with 15% off our XP Booster!"
        }
    },
    "streak_warrior": {
        "name": "Streak Warrior",
        "description": "Maintain your focus streak for 7 consecutive days",
        "icon": "🔥",
        "goal": 7,
        "type": "consecutive_days",
        "reward": {"xp": 200, "special_badge": "streak_warrior"},
        "difficulty": "hard",
        "unlock_offer": {
            "product_id": "streak_saver",
            "discount": 50,
            "message": "Incredible streak! Protect future streaks with 50% off Streak Saver!"
        }
    },
    "theme_explorer": {
        "name": "Theme Explorer",
        "description": "Use 3 different themes in a week", 
        "icon": "🎨",
        "goal": 3,
        "type": "themes_used",
        "reward": {"xp": 100},
        "difficulty": "medium",
        "unlock_offer": {
            "product_id": "premium_theme_pack",
            "discount": 25,
            "message": "Love themes? Unlock premium themes with 25% off!"
        }
    },
    "early_bird": {
        "name": "Early Bird",
        "description": "Complete your first focus session before 9 AM",
        "icon": "🌅", 
        "goal": 1,
        "type": "early_session",
        "reward": {"xp": 30, "morning_badge": True},
        "difficulty": "easy",
        "unlock_offer": {
            "product_id": "custom_sound_pack", 
            "discount": 10,
            "message": "Early starter! Enhance morning sessions with 10% off Sound Packs!"
        }
    }
}

# Advanced Badge & Achievement System - Phase 3 Gamification
BADGE_SYSTEM = {
    "categories": {
        "progression": {
            "name": "Progression Badges",
            "icon": "⭐",
            "description": "Level up your productivity journey"
        },
        "focus": {
            "name": "Focus Master Badges", 
            "icon": "🎯",
            "description": "Deep work and concentration achievements"
        },
        "streak": {
            "name": "Consistency Badges",
            "icon": "🔥", 
            "description": "Daily habit and streak rewards"
        },
        "premium": {
            "name": "Supporter Badges",
            "icon": "👑",
            "description": "Premium subscription achievement badges"
        },
        "special": {
            "name": "Special Event Badges",
            "icon": "🏆",
            "description": "Limited time and rare achievement badges"
        },
        "social": {
            "name": "Community Badges",
            "icon": "👥", 
            "description": "Referral and sharing achievement badges"
        }
    },
    "badges": {
        # Progression Badges (Bronze -> Silver -> Gold -> Platinum)
        "level_rookie": {
            "name": "Rookie Producer",
            "description": "Reach Level 5",
            "icon": "🥉",
            "category": "progression",
            "tier": "bronze",
            "unlock_condition": {"level": 5},
            "reward": {"xp": 50},
            "rarity": "common"
        },
        "level_expert": {
            "name": "Productivity Expert", 
            "description": "Reach Level 15",
            "icon": "🥈",
            "category": "progression", 
            "tier": "silver",
            "unlock_condition": {"level": 15},
            "reward": {"xp": 100},
            "rarity": "uncommon"
        },
        "level_master": {
            "name": "Focus Master",
            "description": "Reach Level 30",
            "icon": "🥇",
            "category": "progression",
            "tier": "gold", 
            "unlock_condition": {"level": 30},
            "reward": {"xp": 200, "special_theme": "master_gold"},
            "rarity": "rare"
        },
        "level_legend": {
            "name": "Productivity Legend",
            "description": "Reach Level 50",
            "icon": "💎",
            "category": "progression",
            "tier": "platinum",
            "unlock_condition": {"level": 50},
            "reward": {"xp": 500, "special_theme": "legend_platinum", "title": "Legend"},
            "rarity": "legendary"
        },
        
        # Focus Achievement Badges
        "focus_beginner": {
            "name": "Focus Starter",
            "description": "Complete 10 focus sessions",
            "icon": "🎯",
            "category": "focus",
            "tier": "bronze",
            "unlock_condition": {"focus_sessions": 10},
            "reward": {"xp": 75},
            "rarity": "common"
        },
        "focus_warrior": {
            "name": "Deep Work Warrior", 
            "description": "Complete 100 focus sessions",
            "icon": "⚔️",
            "category": "focus",
            "tier": "silver",
            "unlock_condition": {"focus_sessions": 100},
            "reward": {"xp": 150, "focus_boost": 1.1},
            "rarity": "uncommon"
        },
        "focus_master": {
            "name": "Concentration Master",
            "description": "Complete 500 focus sessions",
            "icon": "🧠",
            "category": "focus", 
            "tier": "gold",
            "unlock_condition": {"focus_sessions": 500},
            "reward": {"xp": 300, "focus_boost": 1.2},
            "rarity": "rare"
        },
        
        # Streak Achievement Badges
        "streak_starter": {
            "name": "Consistent Starter",
            "description": "Maintain a 3-day streak",
            "icon": "🔥",
            "category": "streak",
            "tier": "bronze", 
            "unlock_condition": {"streak": 3},
            "reward": {"xp": 50},
            "rarity": "common"
        },
        "streak_master": {
            "name": "Streak Master",
            "description": "Maintain a 30-day streak", 
            "icon": "🌟",
            "category": "streak",
            "tier": "gold",
            "unlock_condition": {"streak": 30},
            "reward": {"xp": 400, "streak_protection": 7},
            "rarity": "rare"
        },
        "streak_legend": {
            "name": "Consistency Legend",
            "description": "Maintain a 100-day streak",
            "icon": "⚡",
            "category": "streak", 
            "tier": "platinum",
            "unlock_condition": {"streak": 100},
            "reward": {"xp": 1000, "streak_protection": 14, "title": "Streak Legend"},
            "rarity": "legendary"
        },
        
        # Premium Supporter Badges
        "legacy_supporter": {
            "name": "Legacy Supporter",
            "description": "Early Premium adopter with legacy status",
            "icon": "👑",
            "category": "premium",
            "tier": "special",
            "unlock_condition": {"subscription_tier": "premium"},
            "reward": {"exclusive_theme": "legacy_royal"},
            "rarity": "exclusive"
        },
        "monthly_supporter": {
            "name": "Monthly Supporter", 
            "description": "Active Monthly Premium subscriber",
            "icon": "🎖️",
            "category": "premium",
            "tier": "bronze",
            "unlock_condition": {"subscription_tier": "premium_monthly"},
            "reward": {"subscriber_theme": "monthly_gold"},
            "rarity": "supporter"
        },
        "yearly_supporter": {
            "name": "Yearly Supporter",
            "description": "Committed Yearly Premium subscriber", 
            "icon": "🏅",
            "category": "premium",
            "tier": "silver", 
            "unlock_condition": {"subscription_tier": "premium_yearly"},
            "reward": {"subscriber_theme": "yearly_emerald", "yearly_bonus": 1.1},
            "rarity": "supporter"
        },
        "lifetime_supporter": {
            "name": "Lifetime Supporter",
            "description": "Ultimate FocusFlow Lifetime supporter",
            "icon": "💎",
            "category": "premium",
            "tier": "platinum",
            "unlock_condition": {"subscription_tier": "premium_lifetime"}, 
            "reward": {"subscriber_theme": "lifetime_diamond", "lifetime_bonus": 1.25, "title": "Lifetime Legend"},
            "rarity": "legendary"
        },
        
        # Social/Referral Badges
        "referral_starter": {
            "name": "Friend Inviter",
            "description": "Refer your first friend to FocusFlow",
            "icon": "🤝", 
            "category": "social",
            "tier": "bronze",
            "unlock_condition": {"referrals": 1},
            "reward": {"xp": 100, "commission_bonus": 1.1},
            "rarity": "common"
        },
        "referral_master": {
            "name": "Community Builder",
            "description": "Successfully refer 10 premium users",
            "icon": "👥",
            "category": "social",
            "tier": "gold", 
            "unlock_condition": {"successful_referrals": 10},
            "reward": {"xp": 500, "commission_bonus": 1.25, "referral_boost": "permanent"},
            "rarity": "rare"
        },
        
        # Special Event Badges (Seasonal/Limited)
        "early_adopter": {
            "name": "Early Adopter",
            "description": "Joined FocusFlow in the first month",
            "icon": "🚀",
            "category": "special",
            "tier": "platinum",
            "unlock_condition": {"joined_before": "2025-07-31"},
            "reward": {"exclusive_theme": "early_adopter_special", "title": "Pioneer"},
            "rarity": "exclusive"
        },
        "shop_explorer": {
            "name": "Shop Explorer",
            "description": "Make your first in-app purchase",
            "icon": "🛍️",
            "category": "special", 
            "tier": "bronze",
            "unlock_condition": {"purchases": 1},
            "reward": {"xp": 75, "shop_discount": 5},
            "rarity": "common"
        },
        "power_buyer": {
            "name": "Power Buyer", 
            "description": "Purchase 5 different in-app products",
            "icon": "💳",
            "category": "special",
            "tier": "gold",
            "unlock_condition": {"unique_purchases": 5},
            "reward": {"xp": 300, "shop_discount": 15, "exclusive_products": True},
            "rarity": "rare"
        }
    }
}

# Ghosted Features System - Show premium features to free users with upgrade prompts
GHOSTED_FEATURES = {
    "custom_timers": {
        "feature_name": "Custom Timer Settings",
        "description": "Create personalized focus sessions with custom durations",
        "icon": "⏰",
        "ghost_preview": {
            "90": "Deep Work (90/15 min)", 
            "60": "Power Hour (60/10 min)",
            "45": "Focus Sprint (45/5 min)",
            "120": "Ultra Deep (120/20 min)"
        },
        "upgrade_message": "Unlock custom timers to maximize your deep work potential!",
        "required_tier": "premium_monthly",
        "upgrade_cta": "Upgrade to Premium",
        "preview_limit": 2  # Show 2 options, then show upgrade prompt
    },
    "premium_themes": {
        "feature_name": "Premium Theme Collection", 
        "description": "Beautiful themes designed for enhanced focus and productivity",
        "icon": "🎨",
        "ghost_preview": {
            "darkmode": {"name": "Dark Focus", "colors": ["#1a1a1a", "#8b5cf6"], "preview": "🌙"},
            "focus_black": {"name": "Focus Black", "colors": ["#000000", "#ffffff"], "preview": "⚫"}, 
            "nature_set": {"name": "Nature Calm", "colors": ["#065f46", "#10b981"], "preview": "🌿"},
            "ocean_blue": {"name": "Ocean Deep", "colors": ["#0c4a6e", "#0284c7"], "preview": "🌊"}
        },
        "upgrade_message": "Personalize your workspace with premium themes!",
        "required_tier": "premium_monthly", 
        "upgrade_cta": "Unlock Premium Themes",
        "preview_limit": 1
    },
    "premium_sounds": {
        "feature_name": "Premium Sound Library",
        "description": "High-quality focus sounds and ambient music", 
        "icon": "🎵",
        "ghost_preview": {
            "rain": {"name": "Gentle Rain", "duration": "Looped", "preview": "🌧️"},
            "forest": {"name": "Forest Sounds", "duration": "Looped", "preview": "🌲"},
            "cafe": {"name": "Coffee Shop", "duration": "Looped", "preview": "☕"},
            "ocean": {"name": "Ocean Waves", "duration": "Looped", "preview": "🌊"},
            "fireplace": {"name": "Cozy Fireplace", "duration": "Looped", "preview": "🔥"}
        },
        "upgrade_message": "Enhance focus with premium soundscapes!",
        "required_tier": "premium_monthly",
        "upgrade_cta": "Get Premium Sounds", 
        "preview_limit": 1
    },
    "advanced_analytics": {
        "feature_name": "Advanced Analytics Dashboard",
        "description": "Detailed insights into your productivity patterns",
        "icon": "📊", 
        "ghost_preview": {
            "weekly_trends": {"name": "Weekly Trends", "chart": "line", "preview": "📈"},
            "focus_heatmap": {"name": "Focus Heatmap", "chart": "heatmap", "preview": "🔥"},
            "productivity_score": {"name": "Productivity Score", "chart": "gauge", "preview": "⭐"},
            "goal_tracking": {"name": "Goal Progress", "chart": "progress", "preview": "🎯"}
        },
        "upgrade_message": "Unlock detailed analytics to optimize your productivity!",
        "required_tier": "premium_monthly",
        "upgrade_cta": "View Full Analytics",
        "preview_limit": 1
    },
    "cloud_backup": {
        "feature_name": "Cloud Backup & Sync",
        "description": "Access your data across all devices with automatic backup",
        "icon": "☁️",
        "ghost_preview": {
            "auto_sync": {"name": "Auto Sync", "status": "Available", "preview": "🔄"},
            "device_sync": {"name": "Multi-Device", "devices": 3, "preview": "📱💻"},
            "backup_history": {"name": "Backup History", "backups": 7, "preview": "🗂️"}
        },
        "upgrade_message": "Never lose your progress - sync across all devices!",
        "required_tier": "premium_monthly",
        "upgrade_cta": "Enable Cloud Sync",
        "preview_limit": 1
    },
    "achievement_accelerator": {
        "feature_name": "Achievement Accelerator",
        "description": "Unlock achievements faster and earn bonus XP",
        "icon": "🚀",
        "ghost_preview": {
            "2x_xp": {"name": "2x XP Weekends", "multiplier": 2.0, "preview": "⚡"},
            "bonus_achievements": {"name": "Bonus Achievements", "count": 5, "preview": "🏆"}, 
            "streak_protection": {"name": "Streak Insurance", "days": 7, "preview": "🛡️"}
        },
        "upgrade_message": "Accelerate your progress with premium bonuses!",
        "required_tier": "premium_monthly", 
        "upgrade_cta": "Boost Progress",
        "preview_limit": 1
    }
}

# Models
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: Optional[str] = ""
    status: TaskStatus = TaskStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    xp_earned: int = 10

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class FocusSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    timer_type: TimerType
    duration_minutes: int
    completed: bool = False
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    xp_earned: int = 25

class FocusSessionCreate(BaseModel):
    timer_type: TimerType
    duration_minutes: int

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    subscription_tier: SubscriptionTier = SubscriptionTier.free
    subscription_expires_at: Optional[datetime] = None
    premium_badge: Optional[str] = None  # Badge type for premium users
    total_xp: int = 0
    current_streak: int = 0
    best_streak: int = 0
    level: int = 1
    tasks_completed: int = 0
    focus_sessions_completed: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_date: Optional[datetime] = None
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None  # Referral code of who referred this user
    total_referrals: int = 0
    total_commission_earned: float = 0.0

class UserCreate(BaseModel):
    name: str
    email: str
    referral_code: Optional[str] = None  # Code of person who referred them

class Achievement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    achievement_type: str
    title: str
    description: str
    xp_reward: int
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    package_id: str
    amount: float
    currency: str
    payment_status: PaymentStatus = PaymentStatus.pending
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    referral_code_used: Optional[str] = None  # Referral code used during purchase
    metadata: Dict[str, Any] = {}

class Referral(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    referrer_user_id: str  # User who made the referral
    referred_user_id: str  # User who was referred
    referral_code: str  # Referral code used
    status: ReferralStatus = ReferralStatus.pending
    commission_earned: float = 0.0
    payment_transaction_id: Optional[str] = None  # Transaction that triggered commission
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class Commission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # User earning the commission
    referral_id: str
    amount: float
    status: CommissionStatus = CommissionStatus.pending
    payment_transaction_id: str  # Original transaction that generated commission
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

class SubscriptionRequest(BaseModel):
    package_id: str
    origin_url: str
    referral_code: Optional[str] = None

class CustomTimerPreset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    focus_minutes: int
    short_break_minutes: int
    long_break_minutes: int
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CustomTimerCreate(BaseModel):
    name: str
    focus_minutes: int
    short_break_minutes: int
    long_break_minutes: int

class DailyStats(BaseModel):
    date: datetime
    tasks_completed: int = 0
    focus_sessions_completed: int = 0
    total_focus_time: int = 0
    xp_earned: int = 0

class ReferralStats(BaseModel):
    total_referrals: int
    pending_referrals: int
    completed_referrals: int
    total_commission_earned: float
    pending_commission: float
    paid_commission: float

class Withdrawal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float
    method: str  # "bank_transfer", "paypal", etc.
    status: str = "pending"  # pending, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

class InAppPurchase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    product_id: str
    amount: float
    currency: str
    status: str = "pending"  # pending, completed, failed
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    applied: bool = False  # Whether the reward has been applied

class UserInventory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    themes: List[str] = []  # Unlocked themes
    sounds: List[str] = []  # Unlocked sound packs
    powerups: Dict[str, int] = {}  # Powerup type -> count
    streak_protection_until: Optional[datetime] = None
    instant_achievements_used: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Helper functions
def generate_referral_code(user_id: str, email: str) -> str:
    """Generate a unique referral code for a user"""
    # Create a hash from user ID and email, then take first 8 characters
    hash_input = f"{user_id}{email}{secrets.token_hex(8)}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()

async def get_user_inventory(user_id: str) -> UserInventory:
    """Get or create user inventory"""
    inventory = await db.user_inventory.find_one({"user_id": user_id})
    if not inventory:
        new_inventory = UserInventory(user_id=user_id)
        await db.user_inventory.insert_one(new_inventory.dict())
        return new_inventory
    return UserInventory(**inventory)

async def apply_purchase_rewards(user_id: str, product_id: str):
    """Apply rewards from in-app purchase to user"""
    if product_id not in IN_APP_PRODUCTS:
        return False
    
    product = IN_APP_PRODUCTS[product_id]
    reward = product["reward"]
    inventory = await get_user_inventory(user_id)
    user = await db.users.find_one({"id": user_id})
    
    updates = {}
    inventory_updates = {}
    
    # Apply different types of rewards
    if "xp" in reward:
        # Instant XP boost
        new_xp = user["total_xp"] + reward["xp"]
        new_level = (new_xp // 100) + 1
        updates.update({
            "total_xp": new_xp,
            "level": new_level
        })
    
    if "streak_protection_days" in reward:
        # Streak protection
        protection_until = datetime.utcnow() + timedelta(days=reward["streak_protection_days"])
        inventory_updates["streak_protection_until"] = protection_until
    
    if "themes" in reward:
        # Unlock themes
        current_themes = set(inventory.themes)
        new_themes = set(reward["themes"])
        inventory_updates["themes"] = list(current_themes.union(new_themes))
    
    if "sounds" in reward:
        # Unlock sound packs
        current_sounds = set(inventory.sounds)
        new_sounds = set(reward["sounds"])
        inventory_updates["sounds"] = list(current_sounds.union(new_sounds))
    
    if "powerups" in reward:
        # Add powerups to inventory
        for powerup in reward["powerups"]:
            powerup_type = powerup["type"]
            current_count = inventory.powerups.get(powerup_type, 0)
            inventory.powerups[powerup_type] = current_count + powerup["count"]
        inventory_updates["powerups"] = inventory.powerups
    
    if "instant_achievements" in reward:
        # Unlock random achievements + bonus XP
        bonus_xp = reward.get("bonus_xp", 0)
        achievement_count = reward["instant_achievements"]
        
        # Add bonus XP
        current_xp = updates.get("total_xp", user["total_xp"])
        new_xp = current_xp + bonus_xp
        new_level = (new_xp // 100) + 1
        updates.update({
            "total_xp": new_xp,
            "level": new_level
        })
        
        # Track achievement accelerator usage
        inventory_updates["instant_achievements_used"] = inventory.instant_achievements_used + achievement_count
    
    # Update user if needed
    if updates:
        await db.users.update_one({"id": user_id}, {"$set": updates})
    
    # Update inventory if needed
    if inventory_updates:
        inventory_updates["updated_at"] = datetime.utcnow()
        await db.user_inventory.update_one(
            {"user_id": user_id}, 
            {"$set": inventory_updates},
            upsert=True
        )
    
    return True

async def check_streak_protection(user_id: str) -> bool:
    """Check if user has active streak protection"""
    inventory = await get_user_inventory(user_id)
    if inventory.streak_protection_until:
        return datetime.utcnow() < inventory.streak_protection_until
    return False

async def check_badge_unlocks(user_id: str, user_data: dict = None):
    """Check and award new badges for user"""
    if not user_data:
        user_data = await db.users.find_one({"id": user_id})
        if not user_data:
            return []
    
    # Get existing badges
    existing_badges = await db.user_badges.find({"user_id": user_id}).to_list(None)
    existing_badge_ids = {badge["badge_id"] for badge in existing_badges}
    
    newly_unlocked = []
    
    # Check each badge for unlock conditions
    for badge_id, badge in BADGE_SYSTEM["badges"].items():
        if badge_id in existing_badge_ids:
            continue  # Already has this badge
            
        unlock_condition = badge["unlock_condition"]
        unlocked = False
        
        # Check different unlock conditions
        if "level" in unlock_condition:
            unlocked = user_data.get("level", 1) >= unlock_condition["level"]
        elif "focus_sessions" in unlock_condition:
            unlocked = user_data.get("focus_sessions_completed", 0) >= unlock_condition["focus_sessions"]
        elif "streak" in unlock_condition:
            unlocked = user_data.get("current_streak", 0) >= unlock_condition["streak"]
        elif "subscription_tier" in unlock_condition:
            unlocked = user_data.get("subscription_tier") == unlock_condition["subscription_tier"]
        elif "referrals" in unlock_condition:
            unlocked = user_data.get("total_referrals", 0) >= unlock_condition["referrals"]
        elif "successful_referrals" in unlock_condition:
            # Check from referrals collection
            successful_refs = await db.referrals.count_documents({
                "referrer_user_id": user_id,
                "status": "completed"
            })
            unlocked = successful_refs >= unlock_condition["successful_referrals"]
        elif "purchases" in unlock_condition:
            # Check from in_app_purchases collection
            purchases = await db.in_app_purchases.count_documents({
                "user_id": user_id,
                "status": "completed"
            })
            unlocked = purchases >= unlock_condition["purchases"]
        elif "unique_purchases" in unlock_condition:
            # Check unique products purchased
            unique_purchases = await db.in_app_purchases.distinct("product_id", {
                "user_id": user_id,
                "status": "completed"
            })
            unlocked = len(unique_purchases) >= unlock_condition["unique_purchases"]
        elif "joined_before" in unlock_condition:
            # Check if user joined before a certain date
            join_date = user_data.get("created_at")
            if join_date:
                target_date = datetime.fromisoformat(unlock_condition["joined_before"])
                unlocked = join_date < target_date
        
        if unlocked:
            # Award the badge
            badge_record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "badge_id": badge_id,
                "awarded_at": datetime.utcnow(),
                "badge_data": badge
            }
            
            await db.user_badges.insert_one(badge_record)
            newly_unlocked.append(badge_record)
            
            # Apply badge rewards
            await apply_badge_rewards(user_id, badge)
    
    return newly_unlocked

async def apply_badge_rewards(user_id: str, badge: dict):
    """Apply rewards from badge unlock"""
    reward = badge.get("reward", {})
    updates = {}
    
    # Apply XP reward
    if "xp" in reward:
        user = await db.users.find_one({"id": user_id})
        new_xp = user["total_xp"] + reward["xp"]
        new_level = (new_xp // 100) + 1
        updates.update({
            "total_xp": new_xp,
            "level": new_level
        })
    
    # Apply other rewards (themes, titles, etc.)
    # These would be stored in user inventory or user profile
    inventory_updates = {}
    
    if "special_theme" in reward or "exclusive_theme" in reward or "subscriber_theme" in reward:
        inventory = await get_user_inventory(user_id)
        theme_key = "special_theme" if "special_theme" in reward else (
            "exclusive_theme" if "exclusive_theme" in reward else "subscriber_theme"
        )
        theme_name = reward[theme_key]
        
        if theme_name not in inventory.themes:
            inventory_updates["themes"] = inventory.themes + [theme_name]
    
    if "title" in reward:
        updates["user_title"] = reward["title"]
    
    # Update user if needed
    if updates:
        await db.users.update_one({"id": user_id}, {"$set": updates})
    
    # Update inventory if needed  
    if inventory_updates:
        inventory_updates["updated_at"] = datetime.utcnow()
        await db.user_inventory.update_one(
            {"user_id": user_id},
            {"$set": inventory_updates},
            upsert=True
        )

def get_level_from_xp(xp: int) -> int:
    """Calculate level based on XP (100 XP per level)"""
    return max(1, (xp // 100) + 1)

def get_daily_color_theme():
    """Get color theme based on day of week"""
    themes = {
        0: {"name": "Motivation Monday", "primary": "purple", "secondary": "indigo"},
        1: {"name": "Tranquil Tuesday", "primary": "blue", "secondary": "cyan"},
        2: {"name": "Wonderful Wednesday", "primary": "green", "secondary": "emerald"},
        3: {"name": "Thoughtful Thursday", "primary": "yellow", "secondary": "amber"},
        4: {"name": "Fresh Friday", "primary": "pink", "secondary": "rose"},
        5: {"name": "Serene Saturday", "primary": "teal", "secondary": "cyan"},
        6: {"name": "Soulful Sunday", "primary": "violet", "secondary": "purple"}
    }
    return themes[datetime.now().weekday()]

def get_productivity_theme(user_data: dict):
    """Get adaptive theme based on productivity level (premium feature)"""
    if user_data.get("subscription_tier") != "premium":
        return get_daily_color_theme()
    
    # Calculate productivity score based on recent activity
    today = datetime.utcnow().date()
    today_tasks = user_data.get("tasks_completed_today", 0)
    today_sessions = user_data.get("focus_sessions_completed_today", 0)
    
    productivity_score = (today_tasks * 2) + (today_sessions * 3)  # Weight sessions more
    
    if productivity_score >= 20:
        return {"name": "High Energy", "primary": "green", "secondary": "emerald"}
    elif productivity_score >= 10:
        return {"name": "Steady Progress", "primary": "blue", "secondary": "cyan"}
    elif productivity_score >= 5:
        return {"name": "Getting Started", "primary": "yellow", "secondary": "amber"}
    else:
        return {"name": "Fresh Start", "primary": "purple", "secondary": "indigo"}

# Helper functions
def generate_referral_code(user_id: str, email: str) -> str:
    """Generate a unique referral code for a user"""
    # Create a hash from user ID and email, then take first 8 characters
    hash_input = f"{user_id}{email}{secrets.token_hex(8)}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()

def get_level_from_xp(xp: int) -> int:
    """Calculate level based on XP (100 XP per level)"""
    return max(1, (xp // 100) + 1)

def get_daily_color_theme():
    """Get color theme based on day of week"""
    themes = {
        0: {"name": "Motivation Monday", "primary": "purple", "secondary": "indigo"},
        1: {"name": "Tranquil Tuesday", "primary": "blue", "secondary": "cyan"},
        2: {"name": "Wonderful Wednesday", "primary": "green", "secondary": "emerald"},
        3: {"name": "Thoughtful Thursday", "primary": "yellow", "secondary": "amber"},
        4: {"name": "Fresh Friday", "primary": "pink", "secondary": "rose"},
        5: {"name": "Serene Saturday", "primary": "teal", "secondary": "cyan"},
        6: {"name": "Soulful Sunday", "primary": "violet", "secondary": "purple"}
    }
    return themes[datetime.now().weekday()]

def get_productivity_theme(user_data: dict):
    """Get adaptive theme based on productivity level (premium feature)"""
    if user_data.get("subscription_tier") != "premium":
        return get_daily_color_theme()
    
    # Calculate productivity score based on recent activity
    today = datetime.utcnow().date()
    today_tasks = user_data.get("tasks_completed_today", 0)
    today_sessions = user_data.get("focus_sessions_completed_today", 0)
    
    productivity_score = (today_tasks * 2) + (today_sessions * 3)  # Weight sessions more
    
    if productivity_score >= 20:
        return {"name": "High Energy", "primary": "green", "secondary": "emerald"}
    elif productivity_score >= 10:
        return {"name": "Steady Progress", "primary": "blue", "secondary": "cyan"}
    elif productivity_score >= 5:
        return {"name": "Getting Started", "primary": "yellow", "secondary": "amber"}
    else:
        return {"name": "Fresh Start", "primary": "purple", "secondary": "indigo"}

async def check_and_award_achievements(user_id: str):
    """Check and award achievements to user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return
    
    achievements_to_award = []
    
    # Task completion achievements
    if user["tasks_completed"] >= 10:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "tasks_10"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "tasks_10",
                "title": "Task Warrior",
                "description": "Complete 10 tasks",
                "xp_reward": 50
            })
    
    if user["tasks_completed"] >= 50:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "tasks_50"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "tasks_50",
                "title": "Task Master",
                "description": "Complete 50 tasks",
                "xp_reward": 100
            })
    
    # Focus session achievements
    if user["focus_sessions_completed"] >= 10:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "focus_10"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "focus_10",
                "title": "Focus Apprentice",
                "description": "Complete 10 focus sessions",
                "xp_reward": 75
            })
    
    if user["focus_sessions_completed"] >= 50:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "focus_50"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "focus_50",
                "title": "Focus Master",
                "description": "Complete 50 focus sessions",
                "xp_reward": 150
            })
    
    # Premium subscriber achievement - updated for all premium tiers
    if is_premium_user(user["subscription_tier"]):
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "premium_subscriber"})
        if not existing:
            # Give legacy users special achievement
            if user["subscription_tier"] == "premium":
                title = "Legacy Premium Supporter"
                description = "Early adopter with Legacy Premium status"
            else:
                title = "Premium Supporter" 
                description = "Upgrade to Premium subscription"
                
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "premium_subscriber",
                "title": title,
                "description": description,
                "xp_reward": 200
            })
    
    # Streak achievements
    if user["current_streak"] >= 7:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "streak_7"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "streak_7",
                "title": "Week Warrior",
                "description": "Maintain a 7-day streak",
                "xp_reward": 100
            })
    
    # Award achievements and update user XP
    total_bonus_xp = 0
    for achievement_data in achievements_to_award:
        achievement = Achievement(**achievement_data)
        await db.achievements.insert_one(achievement.dict())
        total_bonus_xp += achievement.xp_reward
    
    if total_bonus_xp > 0:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"total_xp": total_bonus_xp}}
        )

async def process_referral_commission(payment_transaction_id: str, referral_code_used: str, amount_paid: float):
    """Process instant commission payout to referrer when payment completes"""
    if not referral_code_used:
        return
    
    # Find the referrer by their referral code
    referrer = await db.users.find_one({"referral_code": referral_code_used})
    if not referrer:
        logging.warning(f"Referral code {referral_code_used} not found")
        return
    
    # Find the payment transaction to get package info
    transaction = await db.payment_transactions.find_one({"id": payment_transaction_id})
    if not transaction:
        logging.warning(f"Payment transaction {payment_transaction_id} not found")
        return
    
    # Get commission amount from package configuration
    package_id = transaction.get("package_id")
    if package_id and package_id in SUBSCRIPTION_PACKAGES:
        commission_amount = SUBSCRIPTION_PACKAGES[package_id]["commission_amount"]
    else:
        commission_amount = 5.00  # Default fallback
    
    try:
        # Create referral record
        referral = Referral(
            referrer_user_id=referrer["id"],
            referred_user_id=payment_transaction_id,  # Using transaction ID as reference
            referral_code=referral_code_used,
            status=ReferralStatus.completed,
            commission_earned=commission_amount,
            payment_transaction_id=payment_transaction_id
        )
        await db.referrals.insert_one(referral.dict())
        
        # Create commission record
        commission = Commission(
            user_id=referrer["id"],
            referral_id=referral.id,
            amount=commission_amount,
            status=CommissionStatus.paid,  # Mark as paid immediately
            payment_transaction_id=payment_transaction_id,
            paid_at=datetime.utcnow()
        )
        await db.commissions.insert_one(commission.dict())
        
        # Update referrer's stats
        await db.users.update_one(
            {"id": referrer["id"]},
            {
                "$inc": {
                    "total_referrals": 1,
                    "total_commission_earned": commission_amount
                }
            }
        )
        
        # Create instant payout using Stripe
        await process_instant_payout(referrer["id"], commission_amount, referral.id)
        
        # Award referral achievement
        await award_referral_achievement(referrer["id"])
        
        logging.info(f"Processed $5 instant commission for referrer {referrer['id']}")
        
    except Exception as e:
        logging.error(f"Error processing referral commission: {str(e)}")

async def process_instant_payout(user_id: str, amount: float, referral_id: str):
    """Process instant $5 payout to referrer's payment method"""
    try:
        # For now, we'll add the commission as app credit that can be withdrawn
        # In production, you could integrate with Stripe Express accounts for instant bank transfers
        
        # Create a pending withdrawal record that user can claim
        withdrawal = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "amount": amount,
            "currency": "usd",
            "type": "referral_commission",
            "referral_id": referral_id,
            "status": "available_for_withdrawal",
            "created_at": datetime.utcnow()
        }
        
        await db.withdrawals.insert_one(withdrawal)
        
        # You could also integrate with:
        # - Stripe Express for instant bank transfers
        # - PayPal for instant PayPal transfers
        # - Venmo/CashApp APIs for instant mobile payments
        # - Or provide as app credits that reduce future subscription costs
        
        logging.info(f"Created instant withdrawal of ${amount} for user {user_id}")
        
    except Exception as e:
        logging.error(f"Error processing instant payout: {str(e)}")

async def award_referral_achievement(user_id: str):
    """Award achievements for successful referrals"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return
    
    achievements_to_award = []
    
    # First referral achievement
    if user["total_referrals"] >= 1:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "first_referral"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "first_referral",
                "title": "Referral Rookie",
                "description": "Made your first successful referral",
                "xp_reward": 100
            })
    
    # Multiple referral achievements
    if user["total_referrals"] >= 5:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "referral_5"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "referral_5",
                "title": "Referral Champion",
                "description": "Successfully referred 5 users",
                "xp_reward": 250
            })
    
    if user["total_referrals"] >= 10:
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "referral_10"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "referral_10",
                "title": "Referral Master",
                "description": "Successfully referred 10 users - $50 earned!",
                "xp_reward": 500
            })
    
    # Award achievements and bonus XP
    total_bonus_xp = 0
    for achievement_data in achievements_to_award:
        achievement = Achievement(**achievement_data)
        await db.achievements.insert_one(achievement.dict())
        total_bonus_xp += achievement.xp_reward
    
    if total_bonus_xp > 0:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"total_xp": total_bonus_xp}}
        )

async def check_subscription_status(user_id: str):
    """Check if user's subscription is still active"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return False
    
    if user.get("subscription_tier") == "premium":
        expires_at = user.get("subscription_expires_at")
        if expires_at and expires_at < datetime.utcnow():
            # Subscription expired, downgrade to free
            await db.users.update_one(
                {"id": user_id},
                {"$set": {
                    "subscription_tier": "free",
                    "subscription_expires_at": None
                }}
            )
            return False
        return True
    
    return False

def is_premium_user(user_tier: str) -> bool:
    """Check if user has any premium tier access"""
    return user_tier in ["premium", "premium_monthly", "premium_yearly", "premium_lifetime"]

def get_premium_features_for_tier(user_tier: str, premium_badge: str = None) -> dict:
    """Get premium features available for specific tier"""
    if not is_premium_user(user_tier):
        return {
            "custom_timers": False,
            "productivity_themes": False, 
            "premium_sounds": False,
            "xp_bonus": False,
            "cloud_backup": False,
            "premium_achievements": False
        }
    
    # Legacy premium users get special treatment
    if user_tier == "premium":
        return {
            "custom_timers": True,
            "productivity_themes": True,
            "premium_sounds": True, 
            "xp_bonus": True,
            "cloud_backup": True,
            "premium_achievements": True,
            "legacy_user": True,  # Special flag for legacy users
            "badge_type": "legacy_supporter"
        }
    
    # New tier users
    features = {
        "custom_timers": True,
        "productivity_themes": True,
        "premium_sounds": True,
        "xp_bonus": True, 
        "cloud_backup": True,
        "premium_achievements": True,
        "legacy_user": False
    }
    
    if premium_badge:
        features["badge_type"] = premium_badge
        
    return features

# Routes
@api_router.get("/")
async def root():
    return {"message": "FocusFlow API is running!"}

@api_router.get("/theme")
async def get_daily_theme():
    return get_daily_color_theme()

# User routes
@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        # Check subscription status
        await check_subscription_status(existing_user["id"])
        updated_user = await db.users.find_one({"email": user_data.email})
        return User(**updated_user)
    
    # Create new user
    user = User(**user_data.dict())
    user.referral_code = generate_referral_code(user.id, user.email)
    
    # Handle referral if provided
    if user_data.referral_code:
        # Validate referral code exists
        referrer = await db.users.find_one({"referral_code": user_data.referral_code})
        if referrer:
            user.referred_by = user_data.referral_code
        else:
            logging.warning(f"Invalid referral code provided: {user_data.referral_code}")
    
    await db.users.insert_one(user.dict())
    return user

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check subscription status
    await check_subscription_status(user_id)
    user = await db.users.find_one({"id": user_id})
    
    # Update level based on current XP
    new_level = get_level_from_xp(user["total_xp"])
    if new_level != user["level"]:
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"level": new_level}}
        )
        user["level"] = new_level
    
    return User(**user)

@api_router.get("/users/{user_id}/dashboard")
async def get_user_dashboard(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check subscription status
    await check_subscription_status(user_id)
    user = await db.users.find_one({"id": user_id})
    
    # Get today's stats
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_tasks = await db.tasks.count_documents({
        "user_id": user_id,
        "status": "completed",
        "completed_at": {"$gte": today_start, "$lte": today_end}
    })
    
    today_sessions = await db.focus_sessions.count_documents({
        "user_id": user_id,
        "completed": True,
        "completed_at": {"$gte": today_start, "$lte": today_end}
    })
    
    total_focus_time = 0
    sessions = await db.focus_sessions.find({
        "user_id": user_id,
        "completed": True,
        "completed_at": {"$gte": today_start, "$lte": today_end}
    }).to_list(None)
    
    for session in sessions:
        total_focus_time += session["duration_minutes"]
    
    # Get recent achievements
    recent_achievements = await db.achievements.find({
        "user_id": user_id
    }).sort("unlocked_at", -1).limit(3).to_list(None)
    
    # Calculate next level progress
    current_level_xp = (user["level"] - 1) * 100
    next_level_xp = user["level"] * 100
    progress_percentage = min(100, ((user["total_xp"] - current_level_xp) / 100) * 100)
    
    # Get theme based on subscription tier
    user_with_today_stats = {**user, "tasks_completed_today": today_tasks, "focus_sessions_completed_today": today_sessions}
    theme = get_productivity_theme(user_with_today_stats)
    
    return {
        "user": User(**user),
        "today_stats": {
            "tasks_completed": today_tasks,
            "focus_sessions_completed": today_sessions,
            "total_focus_time": total_focus_time,
            "date": today.isoformat()
        },
        "level_progress": {
            "current_level": user["level"],
            "progress_percentage": progress_percentage,
            "xp_to_next_level": max(0, next_level_xp - user["total_xp"])
        },
        "recent_achievements": recent_achievements,
        "theme": theme,
        "premium_features": get_premium_features_for_tier(
            user["subscription_tier"], 
            user.get("premium_badge")
        )
    }

# Task routes
@api_router.post("/users/{user_id}/tasks", response_model=Task)
async def create_task(user_id: str, task_data: TaskCreate):
    task = Task(user_id=user_id, **task_data.dict())
    await db.tasks.insert_one(task.dict())
    return task

@api_router.get("/users/{user_id}/tasks", response_model=List[Task])
async def get_user_tasks(user_id: str, status: Optional[TaskStatus] = None):
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    
    tasks = await db.tasks.find(query).sort("created_at", -1).to_list(None)
    return [Task(**task) for task in tasks]

@api_router.put("/users/{user_id}/tasks/{task_id}", response_model=Task)
async def update_task(user_id: str, task_id: str, task_update: TaskUpdate):
    # Get existing task
    task = await db.tasks.find_one({"id": task_id, "user_id": user_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {}
    if task_update.title is not None:
        update_data["title"] = task_update.title
    if task_update.description is not None:
        update_data["description"] = task_update.description
    if task_update.status is not None:
        update_data["status"] = task_update.status
        if task_update.status == TaskStatus.completed and task["status"] != "completed":
            update_data["completed_at"] = datetime.utcnow()
            # Award XP (premium users get 20% bonus)
            user = await db.users.find_one({"id": user_id})
            xp_bonus = 1.2 if user and user.get("subscription_tier") == "premium" else 1.0
            xp_earned = int(task["xp_earned"] * xp_bonus)
            
            await db.users.update_one(
                {"id": user_id},
                {
                    "$inc": {
                        "total_xp": xp_earned,
                        "tasks_completed": 1
                    },
                    "$set": {"last_activity_date": datetime.utcnow()}
                }
            )
            await check_and_award_achievements(user_id)
    
    await db.tasks.update_one(
        {"id": task_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    updated_task = await db.tasks.find_one({"id": task_id, "user_id": user_id})
    return Task(**updated_task)

@api_router.delete("/users/{user_id}/tasks/{task_id}")
async def delete_task(user_id: str, task_id: str):
    result = await db.tasks.delete_one({"id": task_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Focus session routes
@api_router.post("/users/{user_id}/focus-sessions", response_model=FocusSession)
async def create_focus_session(user_id: str, session_data: FocusSessionCreate):
    session = FocusSession(user_id=user_id, **session_data.dict())
    await db.focus_sessions.insert_one(session.dict())
    return session

@api_router.put("/users/{user_id}/focus-sessions/{session_id}/complete")
async def complete_focus_session(user_id: str, session_id: str):
    session = await db.focus_sessions.find_one({"id": session_id, "user_id": user_id})
    if not session:
        raise HTTPException(status_code=404, detail="Focus session not found")
    
    if session["completed"]:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    await db.focus_sessions.update_one(
        {"id": session_id, "user_id": user_id},
        {
            "$set": {
                "completed": True,
                "completed_at": datetime.utcnow()
            }
        }
    )
    
    # Award XP (premium users get 20% bonus)
    user = await db.users.find_one({"id": user_id})
    xp_bonus = 1.2 if user and user.get("subscription_tier") == "premium" else 1.0
    xp_earned = int(session["xp_earned"] * xp_bonus)
    
    await db.users.update_one(
        {"id": user_id},
        {
            "$inc": {
                "total_xp": xp_earned,
                "focus_sessions_completed": 1
            },
            "$set": {"last_activity_date": datetime.utcnow()}
        }
    )
    
    await check_and_award_achievements(user_id)
    
    updated_session = await db.focus_sessions.find_one({"id": session_id, "user_id": user_id})
    return FocusSession(**updated_session)

@api_router.get("/users/{user_id}/focus-sessions", response_model=List[FocusSession])
async def get_user_focus_sessions(user_id: str, limit: int = 10):
    sessions = await db.focus_sessions.find({"user_id": user_id}).sort("started_at", -1).limit(limit).to_list(None)
    return [FocusSession(**session) for session in sessions]

# Achievement routes
@api_router.get("/users/{user_id}/achievements", response_model=List[Achievement])
async def get_user_achievements(user_id: str):
    achievements = await db.achievements.find({"user_id": user_id}).sort("unlocked_at", -1).to_list(None)
    return [Achievement(**achievement) for achievement in achievements]

# Premium Custom Timer routes (Premium feature)
@api_router.post("/users/{user_id}/custom-timers", response_model=CustomTimerPreset)
async def create_custom_timer(user_id: str, timer_data: CustomTimerCreate):
    user = await db.users.find_one({"id": user_id})
    if not user or not is_premium_user(user.get("subscription_tier")):
        raise HTTPException(status_code=403, detail="Premium subscription required")
    
    timer = CustomTimerPreset(user_id=user_id, **timer_data.dict())
    await db.custom_timers.insert_one(timer.dict())
    return timer

@api_router.get("/users/{user_id}/custom-timers", response_model=List[CustomTimerPreset])
async def get_user_custom_timers(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user or not is_premium_user(user.get("subscription_tier")):
        return []
    
    timers = await db.custom_timers.find({"user_id": user_id, "is_active": True}).to_list(None)
    return [CustomTimerPreset(**timer) for timer in timers]

@api_router.delete("/users/{user_id}/custom-timers/{timer_id}")
async def delete_custom_timer(user_id: str, timer_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user or not is_premium_user(user.get("subscription_tier")):
        raise HTTPException(status_code=403, detail="Premium subscription required")
    
    result = await db.custom_timers.update_one(
        {"id": timer_id, "user_id": user_id},
        {"$set": {"is_active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Timer not found")
    return {"message": "Timer deleted successfully"}

# Subscription and Payment routes
@api_router.get("/subscription/packages")
async def get_subscription_packages():
    """Get available subscription packages"""
    return SUBSCRIPTION_PACKAGES

@app.get("/api/shop/products")
async def get_in_app_products():
    """Get available in-app purchase products"""
    return IN_APP_PRODUCTS

@app.get("/api/users/{user_id}/inventory")
async def get_user_inventory_endpoint(user_id: str):
    """Get user's inventory (unlocked content)"""
    inventory = await get_user_inventory(user_id)
    return {
        "user_id": user_id,
        "themes": inventory.themes,
        "sounds": inventory.sounds,
        "powerups": inventory.powerups,
        "streak_protection_until": inventory.streak_protection_until,
        "instant_achievements_used": inventory.instant_achievements_used
    }

@app.post("/api/shop/purchase")
async def create_in_app_purchase(request: dict):
    """Create in-app purchase"""
    product_id = request.get("product_id")
    user_id = request.get("user_id") 
    origin_url = request.get("origin_url", "https://focusflow.app")
    
    if not product_id or not user_id:
        raise HTTPException(status_code=400, detail="Missing product_id or user_id")
    
    if product_id not in IN_APP_PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = IN_APP_PRODUCTS[product_id]
    
    try:
        # Create Stripe payment intent for small purchase
        intent = stripe.PaymentIntent.create(
            amount=int(product["amount"] * 100),  # Convert to cents
            currency=product["currency"],
            metadata={
                "type": "in_app_purchase",
                "product_id": product_id,
                "user_id": user_id,
                "product_name": product["name"]
            }
        )
        
        # Store purchase record
        purchase = InAppPurchase(
            user_id=user_id,
            product_id=product_id,
            amount=product["amount"],
            currency=product["currency"],
            stripe_payment_intent_id=intent.id,
            status="pending"
        )
        
        await db.in_app_purchases.insert_one(purchase.dict())
        
        return {
            "client_secret": intent.client_secret,
            "purchase_id": purchase.id,
            "product": {
                "name": product["name"],
                "description": product["description"], 
                "amount": product["amount"],
                "currency": product["currency"],
                "icon": product["icon"]
            }
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")

@app.post("/api/shop/confirm-purchase")
async def confirm_in_app_purchase(request: dict):
    """Confirm and apply in-app purchase after payment"""
    purchase_id = request.get("purchase_id")
    payment_intent_id = request.get("payment_intent_id")
    
    if not purchase_id or not payment_intent_id:
        raise HTTPException(status_code=400, detail="Missing purchase_id or payment_intent_id")
    
    # Find the purchase
    purchase = await db.in_app_purchases.find_one({"id": purchase_id})
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    
    # Verify with Stripe
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == "succeeded" and not purchase["applied"]:
            # Apply the rewards
            success = await apply_purchase_rewards(purchase["user_id"], purchase["product_id"])
            
            if success:
                # Mark purchase as completed and applied
                await db.in_app_purchases.update_one(
                    {"id": purchase_id},
                    {
                        "$set": {
                            "status": "completed",
                            "applied": True,
                            "completed_at": datetime.utcnow()
                        }
                    }
                )
                
                return {
                    "status": "success",
                    "message": f"Purchase applied! You received: {IN_APP_PRODUCTS[purchase['product_id']]['description']}",
                    "product": IN_APP_PRODUCTS[purchase["product_id"]]
                }
        
        return {"status": "pending", "message": "Payment still processing"}
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Payment verification error: {str(e)}")

@app.get("/api/users/{user_id}/purchases")
async def get_user_purchases(user_id: str):
    """Get user's purchase history"""
    purchases = await db.in_app_purchases.find({"user_id": user_id}).sort("created_at", -1).to_list(50)
    
    purchase_history = []
    for purchase in purchases:
        product = IN_APP_PRODUCTS.get(purchase["product_id"], {})
        purchase_history.append({
            "id": purchase["id"],
            "product_name": product.get("name", "Unknown Product"),
            "product_icon": product.get("icon", "🛍️"),
            "amount": purchase["amount"],
            "currency": purchase["currency"],
            "status": purchase["status"],
            "applied": purchase["applied"],
            "created_at": purchase["created_at"],
            "completed_at": purchase.get("completed_at")
        })
    
    return purchase_history

@app.get("/api/gamification/badge-system")
async def get_badge_system():
    """Get badge system configuration"""
    return BADGE_SYSTEM

@app.get("/api/users/{user_id}/badges")
async def get_user_badges(user_id: str):
    """Get user's unlocked badges"""
    badges = await db.user_badges.find({"user_id": user_id}).sort("awarded_at", -1).to_list(100)
    
    badge_list = []
    for badge_record in badges:
        badge_data = badge_record["badge_data"]
        badge_list.append({
            "id": badge_record["id"],
            "badge_id": badge_record["badge_id"],
            "name": badge_data["name"],
            "description": badge_data["description"],
            "icon": badge_data["icon"],
            "category": badge_data["category"],
            "tier": badge_data["tier"], 
            "rarity": badge_data["rarity"],
            "awarded_at": badge_record["awarded_at"]
        })
    
    return badge_list

@app.post("/api/users/{user_id}/check-badges")
async def trigger_badge_check(user_id: str):
    """Manually trigger badge unlock check"""
    newly_unlocked = await check_badge_unlocks(user_id)
    
    return {
        "newly_unlocked": len(newly_unlocked),
        "badges": [
            {
                "name": badge["badge_data"]["name"],
                "description": badge["badge_data"]["description"], 
                "icon": badge["badge_data"]["icon"],
                "rarity": badge["badge_data"]["rarity"]
            }
            for badge in newly_unlocked
        ]
    }

@app.get("/api/gamification/ghosted-features")
async def get_ghosted_features():
    """Get ghosted features for free users"""
    return GHOSTED_FEATURES

@app.get("/api/users/{user_id}/badge-progress")
async def get_badge_progress(user_id: str):
    """Get user's progress toward unlocking badges"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get existing badges
    existing_badges = await db.user_badges.find({"user_id": user_id}).to_list(None)
    existing_badge_ids = {badge["badge_id"] for badge in existing_badges}
    
    progress_data = []
    
    for badge_id, badge in BADGE_SYSTEM["badges"].items():
        if badge_id in existing_badge_ids:
            continue  # Already unlocked
            
        unlock_condition = badge["unlock_condition"]
        current_progress = 0
        goal = 0
        progress_type = ""
        
        # Calculate progress for different conditions
        if "level" in unlock_condition:
            current_progress = user.get("level", 1)
            goal = unlock_condition["level"]
            progress_type = "level"
        elif "focus_sessions" in unlock_condition:
            current_progress = user.get("focus_sessions_completed", 0)
            goal = unlock_condition["focus_sessions"]
            progress_type = "focus_sessions"
        elif "streak" in unlock_condition:
            current_progress = user.get("current_streak", 0)
            goal = unlock_condition["streak"]
            progress_type = "streak"
        elif "subscription_tier" in unlock_condition:
            # This is binary - either have it or don't
            current_progress = 1 if user.get("subscription_tier") == unlock_condition["subscription_tier"] else 0
            goal = 1
            progress_type = "subscription"
        
        if goal > 0:
            progress_percentage = min(100, (current_progress / goal) * 100)
            
            progress_data.append({
                "badge_id": badge_id,
                "name": badge["name"],
                "description": badge["description"],
                "icon": badge["icon"],
                "category": badge["category"],
                "tier": badge["tier"],
                "rarity": badge["rarity"],
                "current_progress": current_progress,
                "goal": goal,
                "progress_percentage": progress_percentage,
                "progress_type": progress_type,
                "reward": badge.get("reward", {})
            })
    
    # Sort by progress percentage (closest to completion first)
    progress_data.sort(key=lambda x: x["progress_percentage"], reverse=True)
    
    return progress_data

@api_router.post("/subscription/checkout")
async def create_subscription_checkout(request: SubscriptionRequest):
    """Create Stripe checkout session for subscription with referral tracking"""
    if request.package_id not in SUBSCRIPTION_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package selected")
    
    package = SUBSCRIPTION_PACKAGES[request.package_id]
    
    # Validate referral code if provided
    referrer_info = None
    if request.referral_code:
        referrer = await db.users.find_one({"referral_code": request.referral_code})
        if referrer:
            referrer_info = {"id": referrer["id"], "code": request.referral_code}
        else:
            logging.warning(f"Invalid referral code in checkout: {request.referral_code}")
    
    # Create webhook URL
    webhook_url = f"{request.origin_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Build success and cancel URLs
    success_url = f"{request.origin_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{request.origin_url}/subscription/cancel"
    
    # Create checkout request with referral metadata
    metadata = {
        "package_id": request.package_id,
        "package_name": package["name"]
    }
    
    if referrer_info:
        metadata["referral_code"] = referrer_info["code"]
        metadata["referrer_id"] = referrer_info["id"]
    
    checkout_request = CheckoutSessionRequest(
        amount=package["amount"],
        currency=package["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata
    )
    
    try:
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record with referral info
        payment_transaction = PaymentTransaction(
            user_id="demo_user",  # This would come from authentication
            session_id=session.session_id,
            package_id=request.package_id,
            amount=package["amount"],
            currency=package["currency"],
            payment_status=PaymentStatus.pending,
            referral_code_used=request.referral_code,
            metadata=metadata
        )
        
        await db.payment_transactions.insert_one(payment_transaction.dict())
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "referral_discount": 0,  # Could add discount for referrals in future
            "commission_info": {
                "referrer_earns": package["commission_amount"] if request.referral_code else 0,
                "referral_code_used": request.referral_code
            }
        }
        
    except Exception as e:
        logging.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

@api_router.get("/subscription/status/{session_id}")
async def get_subscription_status(session_id: str):
    """Check subscription payment status and process referral commissions"""
    # Find payment transaction
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If already processed, return current status
    if transaction["payment_status"] in ["completed", "failed", "expired"]:
        return {
            "payment_status": transaction["payment_status"],
            "session_id": session_id,
            "completed_at": transaction.get("completed_at"),
            "referral_commission_processed": bool(transaction.get("referral_code_used"))
        }
    
    # Check with Stripe
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    try:
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction status
        update_data = {
            "payment_status": "completed" if checkout_status.payment_status == "paid" else 
                            "expired" if checkout_status.status == "expired" else "pending"
        }
        
        if update_data["payment_status"] == "completed":
            update_data["completed_at"] = datetime.utcnow()
            
            # Upgrade user to appropriate premium tier
            user_id = transaction["user_id"]
            package = SUBSCRIPTION_PACKAGES[transaction["package_id"]]
            
            # Determine subscription tier based on package
            subscription_tier = package.get("tier", "premium")  # Default to legacy premium
            
            # Calculate subscription expiry (999 months = lifetime)
            if package["duration_months"] >= 999:
                expires_at = datetime.utcnow() + timedelta(days=365 * 10)  # 10 years effectively lifetime
            else:
                expires_at = datetime.utcnow() + timedelta(days=package["duration_months"] * 30)
            
            # Update user with new tier and expiry
            update_fields = {
                "subscription_tier": subscription_tier,
                "subscription_expires_at": expires_at
            }
            
            # Add badge for new tier users
            if package.get("badge"):
                update_fields["premium_badge"] = package["badge"]
            
            await db.users.update_one(
                {"id": user_id},
                {"$set": update_fields}
            )
            
            # Process instant referral commission if applicable
            if transaction.get("referral_code_used"):
                await process_referral_commission(
                    payment_transaction_id=transaction["id"],
                    referral_code_used=transaction["referral_code_used"],
                    amount_paid=transaction["amount"]
                )
            
            # Award premium achievement
            await check_and_award_achievements(user_id)
        
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )
        
        return {
            "payment_status": update_data["payment_status"],
            "session_id": session_id,
            "amount": checkout_status.amount_total / 100,  # Convert from cents
            "currency": checkout_status.currency,
            "completed_at": update_data.get("completed_at"),
            "referral_commission": {
                "processed": bool(transaction.get("referral_code_used")) and update_data["payment_status"] == "completed",
                "amount": 5.00 if transaction.get("referral_code_used") else 0,
                "referral_code": transaction.get("referral_code_used")
            }
        }
        
    except Exception as e:
        logging.error(f"Error checking payment status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check payment status")

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks and process instant referral commissions"""
    try:
        body = await request.body()
        signature = request.headers.get("stripe-signature")
        
        stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.event_type == "checkout.session.completed":
            session_id = webhook_response.session_id
            
            # Find and update payment transaction
            transaction = await db.payment_transactions.find_one({"session_id": session_id})
            if transaction and transaction["payment_status"] == "pending":
                update_data = {
                    "payment_status": "completed",
                    "completed_at": datetime.utcnow()
                }
                
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": update_data}
                )
                
                # Upgrade user to premium
                user_id = transaction["user_id"]
                package = SUBSCRIPTION_PACKAGES[transaction["package_id"]]
                
                expires_at = datetime.utcnow() + timedelta(days=package["duration_months"] * 30)
                
                await db.users.update_one(
                    {"id": user_id},
                    {
                        "$set": {
                            "subscription_tier": "premium",
                            "subscription_expires_at": expires_at
                        }
                    }
                )
                
                # Process instant referral commission if applicable
                if transaction.get("referral_code_used"):
                    await process_referral_commission(
                        payment_transaction_id=transaction["id"],
                        referral_code_used=transaction["referral_code_used"],
                        amount_paid=transaction["amount"]
                    )
                    logging.info(f"Instant $5 commission processed for referral code: {transaction['referral_code_used']}")
                
                await check_and_award_achievements(user_id)
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

# Referral System routes
@api_router.get("/users/{user_id}/referral-stats")
async def get_referral_stats(user_id: str):
    """Get referral statistics for a user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Ensure user has a referral code - generate one if missing
    if not user.get("referral_code"):
        referral_code = generate_referral_code(user["id"], user["email"])
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"referral_code": referral_code}}
        )
        user["referral_code"] = referral_code
    
    # Get referral counts
    total_referrals = await db.referrals.count_documents({"referrer_user_id": user_id})
    completed_referrals = await db.referrals.count_documents({
        "referrer_user_id": user_id, 
        "status": ReferralStatus.completed
    })
    pending_referrals = total_referrals - completed_referrals
    
    # Get commission totals
    commissions = await db.commissions.find({"user_id": user_id}).to_list(None)
    
    total_earned = sum(c["amount"] for c in commissions if c["status"] == CommissionStatus.paid)
    pending_commission = sum(c["amount"] for c in commissions if c["status"] == CommissionStatus.pending)
    
    # Get available withdrawals (balance available for withdrawal)
    withdrawals = await db.withdrawals.find({
        "user_id": user_id, 
        "status": "available_for_withdrawal"
    }).to_list(None)
    
    available_for_withdrawal = sum(w["amount"] for w in withdrawals)
    
    return {
        "referral_code": user["referral_code"],
        "total_referrals": total_referrals,
        "pending_referrals": pending_referrals,
        "completed_referrals": completed_referrals,
        "total_commission_earned": total_earned,
        "pending_commission": pending_commission,
        "available_balance": total_earned,  # Total available balance (same as total_earned for simplicity)
        "available_for_withdrawal": available_for_withdrawal,
        "referral_link": f"https://focusflow.app?ref={user['referral_code']}",
        "earnings_breakdown": {
            "per_referral": 5.00,
            "total_possible": total_referrals * 5.00,
            "total_earned": total_earned
        }
    }

@api_router.get("/users/{user_id}/referrals")
async def get_user_referrals(user_id: str, limit: int = 10):
    """Get referral history for a user"""
    referrals = await db.referrals.find({
        "referrer_user_id": user_id
    }).sort("created_at", -1).limit(limit).to_list(None)
    
    return [Referral(**referral) for referral in referrals]

@api_router.get("/users/{user_id}/withdrawals")
async def get_user_withdrawals(user_id: str):
    """Get available withdrawals for a user"""
    withdrawals = await db.withdrawals.find({
        "user_id": user_id
    }).sort("created_at", -1).to_list(None)
    
    return withdrawals

@api_router.post("/users/{user_id}/withdraw")
async def request_withdrawal(user_id: str, withdrawal_request: dict):
    """Request withdrawal of earned commissions"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get available balance
    available_withdrawals = await db.withdrawals.find({
        "user_id": user_id,
        "status": "available_for_withdrawal"
    }).to_list(None)
    
    total_available = sum(w["amount"] for w in available_withdrawals)
    
    if total_available <= 0:
        raise HTTPException(status_code=400, detail="No balance available for withdrawal")
    
    # In production, this would integrate with:
    # - Stripe Express for bank transfers
    # - PayPal API for PayPal transfers
    # - Other payment providers
    
    # For now, mark withdrawals as requested
    await db.withdrawals.update_many(
        {"user_id": user_id, "status": "available_for_withdrawal"},
        {"$set": {
            "status": "withdrawal_requested",
            "requested_at": datetime.utcnow(),
            "withdrawal_method": withdrawal_request.get("method", "bank_transfer")
        }}
    )
    
    return {
        "message": f"Withdrawal request submitted for ${total_available:.2f}",
        "amount": total_available,
        "status": "requested",
        "processing_time": "3-5 business days"
    }

@api_router.get("/validate-referral/{referral_code}")
async def validate_referral_code(referral_code: str):
    """Validate if referral code exists and get referrer info"""
    referrer = await db.users.find_one({"referral_code": referral_code})
    
    if not referrer:
        return {"valid": False, "message": "Invalid referral code"}
    
    return {
        "valid": True,
        "referrer_name": referrer["name"],
        "commission_amount": 5.00,
        "message": f"Valid referral code! {referrer['name']} will earn $5.00 when you subscribe to Premium.",
        "discount_info": "No discount applied, but your referrer gets rewarded!"
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()