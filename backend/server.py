from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets
import asyncio
import time
from collections import defaultdict
import json
import sys
import traceback

# Stripe integration
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import stripe

# Production Configuration
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Environment Detection
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
DEBUG_MODE = ENVIRONMENT == 'development'

# Enhanced Logging Configuration
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'{ROOT_DIR}/logs/focusflow.log') if ROOT_DIR.joinpath('logs').exists() else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds
rate_limiter = defaultdict(list)

# Database Connection with Production Settings
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=50,  # Production pool size
    minPoolSize=5,
    maxIdleTimeMS=30000,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000
)
db = client[os.environ.get('DB_NAME', 'focusflow_prod')]

# Stripe Configuration with Error Handling
stripe_api_key = os.environ.get('STRIPE_API_KEY')
if not stripe_api_key:
    if ENVIRONMENT == 'production':
        raise ValueError("STRIPE_API_KEY environment variable is required in production")
    else:
        logger.warning("STRIPE_API_KEY not found - payment features will be disabled")
        stripe_api_key = "sk_test_dummy_key_for_development"

stripe.api_key = stripe_api_key

# Security Configuration
security = HTTPBearer(auto_error=False)
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,https://focusflow.app').split(',')

# Application Context Manager for Production
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info(f"Starting FocusFlow server in {ENVIRONMENT} mode")
    
    # Startup
    try:
        # Test database connection
        await client.server_info()
        logger.info("Database connection established")
        
        # Create indexes for production performance
        await create_database_indexes()
        logger.info("Database indexes created/verified")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down FocusFlow server")
    client.close()

# Create FastAPI app with production configuration
app = FastAPI(
    title="FocusFlow API",
    description="Advanced Productivity & Focus Management Platform",
    version="1.0.0",
    debug=DEBUG_MODE,
    lifespan=lifespan,
    docs_url="/docs" if DEBUG_MODE else None,  # Disable docs in production
    redoc_url="/redoc" if DEBUG_MODE else None
)

# Security Middleware
if ENVIRONMENT == 'production':
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,  # 10 minutes cache
)

# Create API router
api_router = APIRouter(prefix="/api")

# Production Error Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error for {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid input data",
            "details": exc.errors() if DEBUG_MODE else "Please check your input format"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP {exc.status_code} for {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"Unhandled error [{error_id}] for {request.url}: {str(exc)}")
    if DEBUG_MODE:
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": str(exc) if DEBUG_MODE else "An unexpected error occurred"
        }
    )

# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests
    rate_limiter[client_ip] = [req_time for req_time in rate_limiter[client_ip] 
                               if current_time - req_time < RATE_LIMIT_WINDOW]
    
    # Check rate limit
    if len(rate_limiter[client_ip]) >= RATE_LIMIT_REQUESTS:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "Rate limit exceeded. Please try again later."}
        )
    
    # Add current request
    rate_limiter[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    if ENVIRONMENT == 'production':
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

async def create_database_indexes():
    """Create database indexes for production performance"""
    try:
        # User indexes
        await db.users.create_index([("id", 1)], unique=True)
        await db.users.create_index([("email", 1)], unique=True)
        await db.users.create_index([("referral_code", 1)])
        
        # Task indexes
        await db.tasks.create_index([("user_id", 1), ("completed", 1)])
        await db.tasks.create_index([("user_id", 1), ("created_at", -1)])
        
        # Focus session indexes
        await db.focus_sessions.create_index([("user_id", 1), ("created_at", -1)])
        
        # Achievement indexes
        await db.achievements.create_index([("user_id", 1)])
        
        # Badge indexes
        await db.user_badges.create_index([("user_id", 1), ("awarded_at", -1)])
        
        # Referral indexes
        await db.referrals.create_index([("referrer_user_id", 1)])
        await db.referrals.create_index([("referred_user_id", 1)])
        
        # Purchase indexes
        await db.in_app_purchases.create_index([("user_id", 1), ("created_at", -1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")

# Input Validation Models with Security

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

async def calculate_productivity_score(user_id: str) -> dict:
    """Calculate comprehensive productivity score"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return {"score": 0, "level": "beginner", "components": {}}
    
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    # Get weekly stats
    tasks_completed = await db.tasks.count_documents({
        "user_id": user_id,
        "completed": True,
        "completed_at": {"$gte": week_ago.isoformat()}
    })
    
    focus_sessions = await db.focus_sessions.count_documents({
        "user_id": user_id,
        "completed_at": {"$gte": week_ago.isoformat()}
    })
    
    # Calculate component scores
    components = {}
    
    # Task completion (0-100)
    task_score = min(100, (tasks_completed / 35) * 100)  # 5 tasks/day * 7 days
    components["task_completion"] = task_score
    
    # Focus consistency (0-100)
    focus_score = min(100, (focus_sessions / 21) * 100)  # 3 sessions/day * 7 days
    components["focus_consistency"] = focus_score
    
    # Streak maintenance (0-100)
    current_streak = user.get("current_streak", 0)
    streak_score = min(100, (current_streak / 30) * 100)  # 30 days max
    components["streak_maintenance"] = streak_score
    
    # Goal achievement (simplified for now)
    goal_score = 50  # Default middle score
    components["goal_achievement"] = goal_score
    
    # Calculate weighted total
    weights = ANALYTICS_SYSTEM["metrics"]["productivity_score"]["components"]
    total_score = (
        task_score * weights["task_completion"]["weight"] +
        focus_score * weights["focus_consistency"]["weight"] +
        streak_score * weights["streak_maintenance"]["weight"] +
        goal_score * weights["goal_achievement"]["weight"]
    )
    
    # Determine level
    ranges = ANALYTICS_SYSTEM["metrics"]["productivity_score"]["ranges"]
    level = "beginner"
    for level_name, range_info in ranges.items():
        if range_info["min"] <= total_score <= range_info["max"]:
            level = level_name
            break
    
    return {
        "score": round(total_score, 1),
        "level": level,
        "components": components,
        "level_info": ranges[level],
        "calculated_at": datetime.utcnow()
    }

async def generate_focus_patterns_analysis(user_id: str) -> dict:
    """Generate detailed focus patterns analysis"""
    # Get last 30 days of focus sessions
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    sessions = await db.focus_sessions.find({
        "user_id": user_id,
        "created_at": {"$gte": thirty_days_ago}
    }).to_list(None)
    
    if not sessions:
        return {"message": "Not enough data for analysis", "sessions_count": 0}
    
    # Time of day analysis
    hour_productivity = {}
    session_lengths = []
    day_of_week_productivity = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    
    for session in sessions:
        created_at = session["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        hour = created_at.hour
        weekday = created_at.weekday()
        duration = session.get("focus_duration", session.get("duration", 25))
        
        hour_productivity[hour] = hour_productivity.get(hour, 0) + 1
        session_lengths.append(duration)
        day_of_week_productivity[weekday] += 1
    
    # Find peak hours
    peak_hour = max(hour_productivity.items(), key=lambda x: x[1])[0] if hour_productivity else 9
    
    # Average session length
    avg_session_length = sum(session_lengths) / len(session_lengths) if session_lengths else 25
    
    # Most productive day
    most_productive_day = max(day_of_week_productivity.items(), key=lambda x: x[1])[0]
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    return {
        "sessions_analyzed": len(sessions),
        "peak_focus_hour": peak_hour,
        "peak_focus_time": f"{peak_hour:02d}:00",
        "average_session_length": round(avg_session_length, 1),
        "most_productive_day": day_names[most_productive_day],
        "hourly_distribution": hour_productivity,
        "weekly_distribution": day_of_week_productivity,
        "recommendations": {
            "optimal_session_length": round(avg_session_length),
            "best_focus_window": f"{peak_hour:02d}:00 - {(peak_hour + 2) % 24:02d}:00",
            "consistency_tip": f"{day_names[most_productive_day]} appears to be your most productive day"
        }
    }

async def create_social_share_content(user_id: str, share_type: str, context: dict) -> dict:
    """Generate social sharing content for achievements"""
    templates = SOCIAL_SHARING["share_templates"].get(share_type, {})
    if not templates:
        return {"error": "Invalid share type"}
    
    share_content = {}
    
    for platform, template in templates["templates"].items():
        platform_info = SOCIAL_SHARING["platforms"][platform]
        hashtags = " ".join(platform_info["hashtags"])
        
        # Format template with context
        formatted_content = template.format(
            hashtags=hashtags,
            **context
        )
        
        # Truncate if needed
        if len(formatted_content) > platform_info["character_limit"]:
            formatted_content = formatted_content[:platform_info["character_limit"] - 3] + "..."
        
        # Generate share URL
        share_url = ""
        if platform == "twitter":
            share_url = f"{platform_info['base_url']}?text={formatted_content}"
        elif platform == "linkedin":
            share_url = f"{platform_info['base_url']}?url=https://focusflow.app&title={templates['title']}&summary={formatted_content}"
        elif platform == "facebook":
            share_url = f"{platform_info['base_url']}?u=https://focusflow.app&quote={formatted_content}"
        
        share_content[platform] = {
            "content": formatted_content,
            "url": share_url,
            "character_count": len(formatted_content),
            "platform_limit": platform_info["character_limit"],
            "icon": platform_info["icon"]
        }
    
    return {
        "share_type": share_type,
        "title": templates["title"],
        "platforms": share_content
    }

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

# Health Check and Status Endpoints
@api_router.get("/health")
async def health_check():
    """Production health check endpoint"""
    try:
        # Test database connection
        await client.server_info()
        database_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_status = "unhealthy"
        
    # Test Stripe connection
    stripe_status = "healthy" if stripe_api_key.startswith("sk_") else "disabled"
    
    health_status = {
        "status": "healthy" if database_status == "healthy" else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "services": {
            "database": database_status,
            "stripe_payments": stripe_status,
            "cache": "healthy"  # Could add Redis check here
        }
    }
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

@api_router.get("/status")
async def api_status():
    """API status and metrics"""
    return {
        "api": "FocusFlow Production API",
        "version": "1.0.0", 
        "environment": ENVIRONMENT,
        "uptime": int(time.time()),  # Simplified uptime
        "endpoints": len([route for route in app.routes]),
        "documentation": f"{os.environ.get('BASE_URL', '')}/docs" if DEBUG_MODE else "disabled"
    }

# Enhanced User Creation with Security
@api_router.post("/users")
async def create_user(user_data: UserCreate):
    """Create new user with enhanced validation"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            logger.warning(f"Attempt to create duplicate user: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="User with this email already exists"
            )
        
        # Create new user with security enhancements
        user = User(
            name=user_data.name,
            email=user_data.email,
            created_at=datetime.utcnow()
        )
        
        # Generate secure referral code
        user.referral_code = generate_referral_code(user.id, user.email)
        
        # Insert user into database
        await db.users.insert_one(user.dict())
        
        # Log user creation (without sensitive data)
        logger.info(f"New user created: {user.id}")
        
        return {"user": user, "message": "User created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

# Enhanced Task Management with Rate Limiting
@api_router.post("/users/{user_id}/tasks")
async def create_task(user_id: str, task_data: TaskCreate):
    """Create new task with enhanced validation"""
    try:
        # Validate user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Rate limiting: max 50 tasks per day per user
        today = datetime.utcnow().date()
        today_tasks = await db.tasks.count_documents({
            "user_id": user_id,
            "created_at": {
                "$gte": datetime.combine(today, datetime.min.time()),
                "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
            }
        })
        
        if today_tasks >= 50:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily task limit reached"
            )
        
        # Create task
        task = Task(
            user_id=user_id,
            title=task_data.title,
            description=task_data.description,
            created_at=datetime.utcnow()
        )
        
        await db.tasks.insert_one(task.dict())
        
        # Check for achievements
        await check_task_achievements(user_id)
        
        logger.info(f"Task created for user {user_id}: {task.id}")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )

async def check_task_achievements(user_id: str):
    """Check and award task-related achievements"""
    try:
        total_tasks = await db.tasks.count_documents({
            "user_id": user_id,
            "completed": True
        })
        
        # Check for task milestone achievements
        milestones = [10, 50, 100, 500, 1000]
        for milestone in milestones:
            if total_tasks >= milestone:
                existing = await db.achievements.find_one({
                    "user_id": user_id,
                    "achievement_type": f"tasks_{milestone}"
                })
                
                if not existing:
                    achievement = Achievement(
                        user_id=user_id,
                        achievement_type=f"tasks_{milestone}",
                        title=f"Task Master {milestone}",
                        description=f"Complete {milestone} tasks",
                        xp_reward=milestone // 10
                    )
                    
                    await db.achievements.insert_one(achievement.dict())
                    
                    # Award XP
                    await db.users.update_one(
                        {"id": user_id},
                        {"$inc": {"total_xp": achievement.xp_reward}}
                    )
                    
                    logger.info(f"Achievement awarded to {user_id}: {achievement.title}")
                    
    except Exception as e:
        logger.error(f"Error checking task achievements for {user_id}: {e}")

# Production-Ready Subscription Handling
@api_router.post("/subscription/checkout")
async def create_subscription_checkout(request: dict):
    """Create subscription checkout with enhanced security"""
    try:
        package_id = request.get("package_id")
        user_id = request.get("user_id")
        origin_url = request.get("origin_url", "")
        referral_code = request.get("referral_code")
        
        # Input validation
        if not package_id or not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: package_id, user_id"
            )
        
        # Validate package exists
        if package_id not in SUBSCRIPTION_PACKAGES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid subscription package"
            )
        
        # Validate user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        package = SUBSCRIPTION_PACKAGES[package_id]
        
        # Security: Validate origin URL
        allowed_origins = CORS_ORIGINS + ['https://focusflow.app', 'https://www.focusflow.app']
        if origin_url and not any(origin_url.startswith(allowed) for allowed in allowed_origins):
            logger.warning(f"Suspicious origin URL: {origin_url}")
            origin_url = "https://focusflow.app"
        
        # Handle referral validation
        referrer_user_id = None
        if referral_code:
            referrer = await validate_referral_code(referral_code)
            if referrer and referrer["id"] != user_id:  # Can't refer yourself
                referrer_user_id = referrer["id"]
        
        try:
            # Create Stripe checkout session with production settings
            checkout_data = {
                "amount": int(package["amount"] * 100),  # Convert to cents
                "currency": package["currency"],
                "success_url": f"{origin_url}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"{origin_url}?payment=cancelled",
                "metadata": {
                    "package_id": package_id,
                    "user_id": user_id,
                    "referrer_user_id": referrer_user_id or "",
                    "commission_amount": str(package["commission_amount"]),
                    "environment": ENVIRONMENT
                }
            }
            
            # Create checkout session
            checkout_response = StripeCheckout().create_session(CheckoutSessionRequest(**checkout_data))
            
            if not checkout_response or not checkout_response.url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create checkout session"
                )
            
            # Store transaction record
            transaction = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "package_id": package_id,
                "amount": package["amount"],
                "currency": package["currency"],
                "status": "pending",
                "stripe_session_id": checkout_response.session_id,
                "referrer_user_id": referrer_user_id,
                "commission_amount": package["commission_amount"] if referrer_user_id else 0,
                "created_at": datetime.utcnow()
            }
            
            await db.transactions.insert_one(transaction)
            
            logger.info(f"Checkout session created: {checkout_response.session_id} for user {user_id}")
            
            return {
                "checkout_url": checkout_response.url,
                "session_id": checkout_response.session_id,
                "package": {
                    "name": package["name"],
                    "amount": package["amount"],
                    "currency": package["currency"]
                }
            }
            
        except Exception as stripe_error:
            logger.error(f"Stripe error: {stripe_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service temporarily unavailable"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription checkout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )

# Enhanced Referral Validation
async def validate_referral_code(referral_code: str) -> Optional[dict]:
    """Validate referral code with security checks"""
    try:
        # Input validation
        if not referral_code or len(referral_code) != 8:
            return None
            
        if not referral_code.isalnum():
            return None
            
        # Find referrer
        referrer = await db.users.find_one({"referral_code": referral_code})
        if not referrer:
            logger.warning(f"Invalid referral code used: {referral_code}")
            return None
            
        return referrer
        
    except Exception as e:
        logger.error(f"Error validating referral code {referral_code}: {e}")
        return None
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

@api_router.get("/gamification/daily-challenges")
async def get_daily_challenges():
    """Get available daily challenges"""
    return DAILY_CHALLENGES

@api_router.get("/users/{user_id}/daily-challenges")
async def get_user_daily_challenges(user_id: str):
    """Get user's daily challenge progress"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    today = datetime.utcnow().date()
    
    # Get today's challenge progress
    challenge_progress = await db.user_daily_challenges.find({
        "user_id": user_id,
        "date": today.isoformat()
    }).to_list(None)
    
    # Convert to dict for easier access
    progress_dict = {cp["challenge_id"]: cp for cp in challenge_progress}
    
    # Build response with challenge status
    challenges_status = []
    
    for challenge_id, challenge in DAILY_CHALLENGES.items():
        progress = progress_dict.get(challenge_id, {})
        current_progress = progress.get("current_progress", 0)
        completed = progress.get("completed", False)
        
        # Calculate current progress based on challenge type
        if challenge["type"] == "focus_sessions":
            current_progress = user.get("focus_sessions_completed", 0)  # Today's sessions
        elif challenge["type"] == "tasks_completed":
            current_progress = user.get("tasks_completed", 0)  # Today's tasks
        elif challenge["type"] == "consecutive_days":
            current_progress = user.get("current_streak", 0)
        
        progress_percentage = min(100, (current_progress / challenge["goal"]) * 100) if challenge["goal"] > 0 else 0
        
        challenges_status.append({
            "challenge_id": challenge_id,
            "name": challenge["name"],
            "description": challenge["description"],
            "icon": challenge["icon"],
            "goal": challenge["goal"],
            "current_progress": current_progress,
            "progress_percentage": progress_percentage,
            "completed": completed,
            "difficulty": challenge["difficulty"],
            "reward": challenge["reward"],
            "unlock_offer": challenge.get("unlock_offer", {}) if completed else None
        })
    
    return {
        "date": today.isoformat(),
        "challenges": challenges_status,
        "completed_today": len([c for c in challenges_status if c["completed"]]),
        "total_challenges": len(challenges_status)
    }

# Phase 4 Advanced Features API Endpoints

@app.get("/api/analytics/system-config")
async def get_analytics_system_config():
    """Get analytics system configuration"""
    return ANALYTICS_SYSTEM

@app.get("/api/users/{user_id}/productivity-score")
async def get_user_productivity_score(user_id: str):
    """Get user's comprehensive productivity score"""
    return await calculate_productivity_score(user_id)

@app.get("/api/users/{user_id}/focus-patterns")
async def get_user_focus_patterns(user_id: str):
    """Get detailed focus patterns analysis"""
    return await generate_focus_patterns_analysis(user_id)

@app.get("/api/users/{user_id}/analytics-dashboard")
async def get_analytics_dashboard(user_id: str):
    """Get complete analytics dashboard data"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all analytics components
    productivity_score = await calculate_productivity_score(user_id)
    focus_patterns = await generate_focus_patterns_analysis(user_id)
    
    # Get recent achievements and badges
    recent_badges = await db.user_badges.find({"user_id": user_id}).sort("awarded_at", -1).limit(5).to_list(5)
    badge_count = await db.user_badges.count_documents({"user_id": user_id})
    
    # Get activity summary (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_tasks = await db.tasks.count_documents({
        "user_id": user_id,
        "completed": True,
        "completed_at": {"$gte": thirty_days_ago.isoformat()}
    })
    
    recent_sessions = await db.focus_sessions.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": thirty_days_ago}
    })
    
    return {
        "user_id": user_id,
        "generated_at": datetime.utcnow(),
        "productivity_score": productivity_score,
        "focus_patterns": focus_patterns,
        "activity_summary": {
            "tasks_completed_30d": recent_tasks,
            "focus_sessions_30d": recent_sessions,
            "current_level": user.get("level", 1),
            "total_xp": user.get("total_xp", 0),
            "current_streak": user.get("current_streak", 0),
            "badges_earned": badge_count
        },
        "recent_achievements": [
            {
                "name": badge["badge_data"]["name"],
                "icon": badge["badge_data"]["icon"],
                "awarded_at": badge["awarded_at"]
            }
            for badge in recent_badges
        ]
    }

@app.get("/api/social/sharing-config")
async def get_social_sharing_config():
    """Get social sharing system configuration"""
    return SOCIAL_SHARING

@app.post("/api/users/{user_id}/social-share")
async def create_social_share(user_id: str, request: dict):
    """Generate social sharing content"""
    share_type = request.get("share_type")
    context = request.get("context", {})
    
    if not share_type:
        raise HTTPException(status_code=400, detail="Missing share_type")
    
    share_content = await create_social_share_content(user_id, share_type, context)
    
    # Log the share attempt
    share_log = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "share_type": share_type,
        "context": context,
        "generated_at": datetime.utcnow(),
        "content": share_content
    }
    
    await db.social_shares.insert_one(share_log)
    
    return share_content

@app.get("/api/users/{user_id}/social-shares")
async def get_user_social_shares(user_id: str):
    """Get user's social sharing history"""
    shares = await db.social_shares.find({"user_id": user_id}).sort("generated_at", -1).limit(20).to_list(20)
    return shares

@app.get("/api/cloud-sync/config")
async def get_cloud_sync_config():
    """Get cloud sync system configuration"""
    return CLOUD_SYNC

@app.get("/api/users/{user_id}/devices")
async def get_user_devices(user_id: str):
    """Get user's registered devices"""
    devices = await db.user_devices.find({"user_id": user_id}).to_list(None)
    return devices

@app.post("/api/users/{user_id}/sync-data")
async def sync_user_data(user_id: str, request: dict):
    """Perform data synchronization for user"""
    device_id = request.get("device_id")
    sync_type = request.get("sync_type", "periodic")
    data_types = request.get("data_types", [])
    
    if not device_id:
        raise HTTPException(status_code=400, detail="Missing device_id")
    
    # Register/update device
    device_info = {
        "device_id": device_id,
        "user_id": user_id,
        "device_type": request.get("device_type", "web"),
        "last_sync": datetime.utcnow(),
        "sync_type": sync_type,
        "app_version": request.get("app_version", "1.0.0")
    }
    
    await db.user_devices.update_one(
        {"user_id": user_id, "device_id": device_id},
        {"$set": device_info},
        upsert=True
    )
    
    # Get data to sync based on requested types
    sync_data = {}
    
    if not data_types or "user_profile" in data_types:
        user = await db.users.find_one({"id": user_id})
        sync_data["user_profile"] = user
    
    if not data_types or "tasks" in data_types:
        tasks = await db.tasks.find({"user_id": user_id}).limit(100).to_list(100)
        sync_data["tasks"] = tasks
    
    if not data_types or "badges" in data_types:
        badges = await db.user_badges.find({"user_id": user_id}).to_list(None)
        sync_data["badges"] = badges
    
    if not data_types or "inventory" in data_types:
        inventory = await get_user_inventory(user_id)
        sync_data["inventory"] = inventory.dict()
    
    return {
        "sync_timestamp": datetime.utcnow(),
        "device_id": device_id,
        "sync_type": sync_type,
        "data_types_synced": list(sync_data.keys()),
        "data": sync_data
    }

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

# Advanced Analytics & Progress Tracking System - Phase 4
ANALYTICS_SYSTEM = {
    "metrics": {
        "productivity_score": {
            "name": "Productivity Score",
            "description": "Overall productivity rating based on tasks, focus time, and consistency",
            "calculation": "weighted_average",
            "components": {
                "task_completion": {"weight": 0.3, "max_points": 100},
                "focus_consistency": {"weight": 0.3, "max_points": 100}, 
                "streak_maintenance": {"weight": 0.2, "max_points": 100},
                "goal_achievement": {"weight": 0.2, "max_points": 100}
            },
            "ranges": {
                "beginner": {"min": 0, "max": 30, "color": "#ef4444", "icon": "🌱"},
                "developing": {"min": 31, "max": 60, "color": "#f97316", "icon": "🌿"},
                "proficient": {"min": 61, "max": 80, "color": "#eab308", "icon": "🌳"},
                "expert": {"min": 81, "max": 95, "color": "#22c55e", "icon": "🏆"},
                "master": {"min": 96, "max": 100, "color": "#8b5cf6", "icon": "👑"}
            }
        },
        "focus_patterns": {
            "name": "Focus Patterns Analysis",
            "description": "Deep dive into when and how you focus best",
            "analysis_types": {
                "time_of_day": "Peak focus hours identification",
                "session_length": "Optimal session duration analysis", 
                "break_patterns": "Most effective break timing",
                "weekly_trends": "Day-of-week productivity patterns",
                "monthly_cycles": "Long-term productivity cycles"
            }
        },
        "goal_tracking": {
            "name": "Goal Achievement Tracking",
            "description": "Advanced goal setting and achievement monitoring",
            "goal_types": {
                "daily_targets": {"tasks": "int", "focus_time": "minutes", "sessions": "int"},
                "weekly_goals": {"streak_days": "int", "total_tasks": "int", "focus_hours": "float"},
                "monthly_objectives": {"level_target": "int", "badge_goals": "int", "habit_building": "days"},
                "custom_challenges": {"user_defined": "flexible", "deadline": "date", "reward": "custom"}
            }
        }
    },
    "visualizations": {
        "heatmaps": {
            "activity_heatmap": "24/7 activity visualization",
            "productivity_calendar": "Monthly productivity overview",
            "focus_intensity": "Session quality heatmap"
        },
        "trend_charts": {
            "productivity_trend": "Long-term productivity changes",
            "focus_time_trend": "Focus duration over time",
            "streak_history": "Consistency tracking chart",
            "xp_growth": "Experience point progression"
        },
        "comparative_analytics": {
            "weekly_comparison": "Week-over-week analysis",
            "monthly_summary": "Month-over-month insights", 
            "goal_vs_actual": "Target vs achievement comparison",
            "peer_benchmarks": "Anonymous user comparisons"
        }
    }
}

# Social Sharing System - Phase 4
SOCIAL_SHARING = {
    "platforms": {
        "twitter": {
            "name": "Twitter",
            "icon": "🐦",
            "character_limit": 280,
            "image_support": True,
            "hashtags": ["#FocusFlow", "#Productivity", "#DeepWork", "#Achievement"],
            "base_url": "https://twitter.com/intent/tweet"
        },
        "linkedin": {
            "name": "LinkedIn", 
            "icon": "💼",
            "character_limit": 1300,
            "image_support": True,
            "hashtags": ["#Productivity", "#ProfessionalDevelopment", "#Focus", "#Success"],
            "base_url": "https://www.linkedin.com/sharing/share-offsite"
        },
        "facebook": {
            "name": "Facebook",
            "icon": "📘", 
            "character_limit": 63206,
            "image_support": True,
            "hashtags": ["#ProductivityTips", "#FocusFlow", "#Achievement"],
            "base_url": "https://www.facebook.com/sharer/sharer.php"
        },
        "instagram": {
            "name": "Instagram Stories",
            "icon": "📸",
            "image_required": True,
            "story_format": True,
            "hashtags": ["#productivity", "#focus", "#achievement", "#goals"],
            "base_url": "https://www.instagram.com/stories"
        }
    },
    "share_templates": {
        "badge_unlock": {
            "title": "🎉 New Badge Unlocked!",
            "templates": {
                "twitter": "Just unlocked the '{badge_name}' badge on @FocusFlow! 🏆 {badge_description} My productivity journey continues! {hashtags}",
                "linkedin": "Excited to share that I've unlocked the '{badge_name}' badge in my productivity journey with FocusFlow! 🏆\n\n{badge_description}\n\nConsistent effort and focus really do pay off. What productivity tools are helping you stay focused? {hashtags}",
                "facebook": "🎉 Achievement Unlocked! Just earned the '{badge_name}' badge on FocusFlow! {badge_description} Love seeing the progress in my productivity journey. Who else is working on building better focus habits? {hashtags}"
            }
        },
        "streak_milestone": {
            "title": "🔥 Streak Milestone!",
            "templates": {
                "twitter": "🔥 {streak_days} day focus streak on @FocusFlow! Consistency is key to productivity. Who's joining me in building better habits? {hashtags}",
                "linkedin": "Celebrating a {streak_days}-day consistency streak with FocusFlow! 🔥\n\nBuilding productive habits one day at a time. The compound effect of small daily actions continues to amaze me.\n\n#Consistency #ProductivityHabits #FocusFlow",
                "facebook": "🔥 Big milestone alert! Just hit a {streak_days} day productivity streak using FocusFlow! The power of showing up every day is incredible. Building better habits one focus session at a time! {hashtags}"
            }
        },
        "level_achievement": {
            "title": "📈 Level Up!",
            "templates": {
                "twitter": "📈 Just reached Level {level} on @FocusFlow! {xp} XP and counting. The journey to better focus continues! {hashtags}",
                "linkedin": "Level {level} achieved in my productivity journey! 🚀\n\nReached {xp} experience points through consistent focus sessions and task completion. Each level represents real growth in focus and productivity skills.\n\n{hashtags}",
                "facebook": "🚀 Level Up! Just reached Level {level} on FocusFlow with {xp} XP! Each level represents hours of focused work and completed tasks. Loving this gamified approach to productivity! {hashtags}"
            }
        },
        "challenge_completion": {
            "title": "✅ Challenge Complete!",
            "templates": {
                "twitter": "✅ Completed the '{challenge_name}' challenge on @FocusFlow! {challenge_description} Feeling accomplished! {hashtags}",
                "linkedin": "Challenge completed! 🎯\n\nJust finished the '{challenge_name}' challenge on FocusFlow: {challenge_description}\n\nThese daily challenges are a great way to build consistent productivity habits. What challenges are you taking on? {hashtags}",
                "facebook": "🎯 Challenge conquered! Just completed the '{challenge_name}' challenge on FocusFlow! {challenge_description} These little daily wins really add up to big progress! {hashtags}"
            }
        }
    }
}

# Cloud Sync & Multi-Device System - Phase 4
CLOUD_SYNC = {
    "sync_strategies": {
        "real_time": {
            "name": "Real-time Sync",
            "description": "Immediate synchronization across all devices",
            "update_frequency": "immediate",
            "conflict_resolution": "last_write_wins",
            "data_types": ["active_session", "task_updates", "timer_state"]
        },
        "periodic": {
            "name": "Periodic Sync", 
            "description": "Regular background synchronization",
            "update_frequency": "5_minutes",
            "conflict_resolution": "merge_strategy",
            "data_types": ["completed_tasks", "session_history", "achievements", "badges"]
        },
        "on_demand": {
            "name": "Manual Sync",
            "description": "User-initiated synchronization",
            "update_frequency": "user_triggered",
            "conflict_resolution": "user_choice",
            "data_types": ["full_backup", "settings", "preferences"]
        }
    },
    "data_categories": {
        "critical": {
            "priority": 1,
            "sync_strategy": "real_time",
            "data": ["user_profile", "subscription_status", "active_sessions", "current_tasks"]
        },
        "important": {
            "priority": 2, 
            "sync_strategy": "periodic",
            "data": ["task_history", "focus_sessions", "achievements", "badges", "streak_data"]
        },
        "supplementary": {
            "priority": 3,
            "sync_strategy": "on_demand", 
            "data": ["themes", "preferences", "analytics_cache", "social_shares"]
        }
    },
    "device_management": {
        "max_devices": 5,
        "device_types": ["desktop", "tablet", "mobile", "web"],
        "device_identification": "uuid_based",
        "last_sync_tracking": True,
        "conflict_indicators": True
    }
}

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()