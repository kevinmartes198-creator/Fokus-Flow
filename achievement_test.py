#!/usr/bin/env python3
"""
Extended Backend Testing - Achievement System Verification
Tests achievement unlocking by creating sufficient activity
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://80fd7c99-1920-47e4-ae5f-404c0c477c86.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

def make_request(method: str, endpoint: str, data: dict = None):
    """Make HTTP request and return (success, response_data, status_code)"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=HEADERS, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=HEADERS, json=data, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=HEADERS, json=data, timeout=10)
        else:
            return False, {"error": "Invalid method"}, 400
            
        return response.status_code < 400, response.json() if response.content else {}, response.status_code
    except Exception as e:
        return False, {"error": str(e)}, 0

def test_achievement_unlocking():
    """Test achievement system by creating enough activity to unlock achievements"""
    print("🏆 Testing Achievement System with Sufficient Activity")
    print("=" * 60)
    
    # Create a new user for this test
    user_data = {
        "name": "Alex Chen",
        "email": "alex.chen@focusflow.com"
    }
    
    success, user_response, _ = make_request("POST", "/users", user_data)
    if not success:
        print("❌ Failed to create test user")
        return
    
    user_id = user_response["id"]
    print(f"✅ Created test user: {user_response['name']} (ID: {user_id[:8]}...)")
    
    # Create and complete 12 tasks to trigger "Task Warrior" achievement (10 tasks)
    print("\n📝 Creating and completing 12 tasks...")
    task_titles = [
        "Complete project proposal", "Review code changes", "Update documentation",
        "Attend team meeting", "Fix critical bug", "Write unit tests",
        "Deploy to staging", "Review pull requests", "Update dependencies",
        "Optimize database queries", "Create user guide", "Plan sprint goals"
    ]
    
    completed_tasks = 0
    for i, title in enumerate(task_titles):
        # Create task
        task_data = {"title": title, "description": f"Task {i+1} description"}
        success, task_response, _ = make_request("POST", f"/users/{user_id}/tasks", task_data)
        
        if success:
            task_id = task_response["id"]
            
            # Complete task
            update_data = {"status": "completed"}
            success, _, _ = make_request("PUT", f"/users/{user_id}/tasks/{task_id}", update_data)
            
            if success:
                completed_tasks += 1
                print(f"  ✅ Completed task {completed_tasks}: {title}")
            else:
                print(f"  ❌ Failed to complete task: {title}")
        else:
            print(f"  ❌ Failed to create task: {title}")
        
        time.sleep(0.1)  # Small delay to avoid overwhelming the API
    
    print(f"\n📊 Completed {completed_tasks} tasks")
    
    # Create and complete 12 focus sessions to trigger "Focus Apprentice" achievement (10 sessions)
    print("\n⏰ Creating and completing 12 focus sessions...")
    
    completed_sessions = 0
    for i in range(12):
        # Create focus session
        session_data = {
            "timer_type": "focus",
            "duration_minutes": 25
        }
        success, session_response, _ = make_request("POST", f"/users/{user_id}/focus-sessions", session_data)
        
        if success:
            session_id = session_response["id"]
            
            # Complete session
            success, _, _ = make_request("PUT", f"/users/{user_id}/focus-sessions/{session_id}/complete")
            
            if success:
                completed_sessions += 1
                print(f"  ✅ Completed focus session {completed_sessions}")
            else:
                print(f"  ❌ Failed to complete focus session {i+1}")
        else:
            print(f"  ❌ Failed to create focus session {i+1}")
        
        time.sleep(0.1)  # Small delay
    
    print(f"\n📊 Completed {completed_sessions} focus sessions")
    
    # Check user stats
    print("\n👤 Checking user stats...")
    success, user_data, _ = make_request("GET", f"/users/{user_id}")
    
    if success:
        print(f"  Total XP: {user_data['total_xp']}")
        print(f"  Level: {user_data['level']}")
        print(f"  Tasks Completed: {user_data['tasks_completed']}")
        print(f"  Focus Sessions Completed: {user_data['focus_sessions_completed']}")
        
        # Expected XP: 12 tasks * 10 XP + 12 sessions * 25 XP = 120 + 300 = 420 XP
        expected_xp = (completed_tasks * 10) + (completed_sessions * 25)
        print(f"  Expected XP: {expected_xp}")
        
        if user_data['total_xp'] >= expected_xp:
            print("  ✅ XP calculation correct")
        else:
            print(f"  ❌ XP mismatch: got {user_data['total_xp']}, expected {expected_xp}")
    
    # Check achievements
    print("\n🏆 Checking achievements...")
    success, achievements, _ = make_request("GET", f"/users/{user_id}/achievements")
    
    if success:
        print(f"  Total achievements unlocked: {len(achievements)}")
        
        expected_achievements = []
        if completed_tasks >= 10:
            expected_achievements.append("Task Warrior (10 tasks)")
        if completed_tasks >= 50:
            expected_achievements.append("Task Master (50 tasks)")
        if completed_sessions >= 10:
            expected_achievements.append("Focus Apprentice (10 sessions)")
        if completed_sessions >= 50:
            expected_achievements.append("Focus Master (50 sessions)")
        
        print(f"  Expected achievements: {len(expected_achievements)}")
        
        if len(achievements) > 0:
            print("  🎉 Unlocked achievements:")
            for achievement in achievements:
                print(f"    • {achievement['title']}: {achievement['description']} (+{achievement['xp_reward']} XP)")
        else:
            print("  ❌ No achievements unlocked")
        
        # Verify specific achievements
        achievement_types = [a['achievement_type'] for a in achievements]
        
        if completed_tasks >= 10 and 'tasks_10' in achievement_types:
            print("  ✅ Task Warrior achievement unlocked correctly")
        elif completed_tasks >= 10:
            print("  ❌ Task Warrior achievement should be unlocked")
        
        if completed_sessions >= 10 and 'focus_10' in achievement_types:
            print("  ✅ Focus Apprentice achievement unlocked correctly")
        elif completed_sessions >= 10:
            print("  ❌ Focus Apprentice achievement should be unlocked")
    else:
        print("  ❌ Failed to retrieve achievements")
    
    # Test dashboard with achievements
    print("\n📊 Testing dashboard with achievements...")
    success, dashboard, _ = make_request("GET", f"/users/{user_id}/dashboard")
    
    if success:
        recent_achievements = dashboard.get('recent_achievements', [])
        print(f"  Recent achievements in dashboard: {len(recent_achievements)}")
        
        if len(recent_achievements) > 0:
            print("  ✅ Dashboard shows recent achievements")
            for achievement in recent_achievements[:3]:  # Show first 3
                print(f"    • {achievement['title']}")
        else:
            print("  ⚠️  No recent achievements in dashboard")
    else:
        print("  ❌ Failed to retrieve dashboard")
    
    print("\n" + "=" * 60)
    print("🎯 Achievement Testing Complete")
    
    return completed_tasks, completed_sessions, len(achievements) if success else 0

if __name__ == "__main__":
    test_achievement_unlocking()