from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from enum import Enum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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
    total_xp: int = 0
    current_streak: int = 0
    best_streak: int = 0
    level: int = 1
    tasks_completed: int = 0
    focus_sessions_completed: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_date: Optional[datetime] = None

class UserCreate(BaseModel):
    name: str
    email: str

class Achievement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    achievement_type: str
    title: str
    description: str
    xp_reward: int
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)

class DailyStats(BaseModel):
    date: datetime
    tasks_completed: int = 0
    focus_sessions_completed: int = 0
    total_focus_time: int = 0
    xp_earned: int = 0

# Helper functions
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
        return User(**existing_user)
    
    user = User(**user_data.dict())
    await db.users.insert_one(user.dict())
    return user

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
        "theme": get_daily_color_theme()
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
            # Award XP
            await db.users.update_one(
                {"id": user_id},
                {
                    "$inc": {
                        "total_xp": task["xp_earned"],
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
    
    # Award XP
    await db.users.update_one(
        {"id": user_id},
        {
            "$inc": {
                "total_xp": session["xp_earned"],
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