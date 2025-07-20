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
    premium = "premium"

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
    
    # Premium subscriber achievement
    if user["subscription_tier"] == "premium":
        existing = await db.achievements.find_one({"user_id": user_id, "achievement_type": "premium_subscriber"})
        if not existing:
            achievements_to_award.append({
                "user_id": user_id,
                "achievement_type": "premium_subscriber",
                "title": "Premium Supporter",
                "description": "Upgrade to Premium subscription",
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
    
    commission_amount = 5.00  # $5 instant commission
    
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
        "premium_features": {
            "custom_timers": user["subscription_tier"] == "premium",
            "productivity_themes": user["subscription_tier"] == "premium",
            "premium_sounds": user["subscription_tier"] == "premium",
            "advanced_analytics": user["subscription_tier"] == "premium"
        }
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
    if not user or user.get("subscription_tier") != "premium":
        raise HTTPException(status_code=403, detail="Premium subscription required")
    
    timer = CustomTimerPreset(user_id=user_id, **timer_data.dict())
    await db.custom_timers.insert_one(timer.dict())
    return timer

@api_router.get("/users/{user_id}/custom-timers", response_model=List[CustomTimerPreset])
async def get_user_custom_timers(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user or user.get("subscription_tier") != "premium":
        return []
    
    timers = await db.custom_timers.find({"user_id": user_id, "is_active": True}).to_list(None)
    return [CustomTimerPreset(**timer) for timer in timers]

@api_router.delete("/users/{user_id}/custom-timers/{timer_id}")
async def delete_custom_timer(user_id: str, timer_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user or user.get("subscription_tier") != "premium":
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
                "referrer_earns": 5.00 if request.referral_code else 0,
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
            
            # Upgrade user to premium (using demo user for now)
            user_id = transaction["user_id"]
            package = SUBSCRIPTION_PACKAGES[transaction["package_id"]]
            
            # Calculate subscription expiry
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