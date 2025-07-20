#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for FocusFlow Productivity App
Tests all high-priority backend functionality systematically
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://80fd7c99-1920-47e4-ae5f-404c0c477c86.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class FocusFlowTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_user_id = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=10)
            else:
                return False, {"error": "Invalid method"}, 400
                
            return response.status_code < 400, response.json() if response.content else {}, response.status_code
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}, 0
        except json.JSONDecodeError:
            return False, {"error": "Invalid JSON response"}, response.status_code if 'response' in locals() else 0

    def test_api_health(self):
        """Test if API is running"""
        print("\n🔍 Testing API Health...")
        success, data, status_code = self.make_request("GET", "/")
        
        if success and status_code == 200:
            self.log_test("API Health Check", True, f"API is running: {data.get('message', 'OK')}")
        else:
            self.log_test("API Health Check", False, f"Status: {status_code}, Error: {data}")

    def test_daily_theme_api(self):
        """Test Daily Theme API"""
        print("\n🎨 Testing Daily Theme API...")
        success, data, status_code = self.make_request("GET", "/theme")
        
        if success and status_code == 200:
            required_fields = ["name", "primary", "secondary"]
            if all(field in data for field in required_fields):
                self.log_test("Daily Theme API", True, f"Theme: {data['name']} - {data['primary']}/{data['secondary']}")
            else:
                self.log_test("Daily Theme API", False, f"Missing required fields in response: {data}")
        else:
            self.log_test("Daily Theme API", False, f"Status: {status_code}, Error: {data}")

    def test_user_management(self):
        """Test User Management API - Create and retrieve users"""
        print("\n👤 Testing User Management API...")
        
        # Test user creation
        user_data = {
            "name": "Sarah Johnson",
            "email": "sarah.johnson@focusflow.com"
        }
        
        success, data, status_code = self.make_request("POST", "/users", user_data)
        
        if success and status_code == 200:
            # Verify user data structure
            required_fields = ["id", "name", "email", "subscription_tier", "total_xp", "level", "current_streak"]
            if all(field in data for field in required_fields):
                self.test_user_id = data["id"]
                self.log_test("User Creation", True, f"Created user: {data['name']} (ID: {data['id'][:8]}...)")
                
                # Verify initial values
                if data["total_xp"] == 0 and data["level"] == 1 and data["subscription_tier"] == "free":
                    self.log_test("User Initial Values", True, "XP=0, Level=1, Tier=free")
                else:
                    self.log_test("User Initial Values", False, f"Unexpected values: XP={data['total_xp']}, Level={data['level']}, Tier={data['subscription_tier']}")
            else:
                self.log_test("User Creation", False, f"Missing required fields: {data}")
        else:
            self.log_test("User Creation", False, f"Status: {status_code}, Error: {data}")
            return
        
        # Test user retrieval
        if self.test_user_id:
            success, data, status_code = self.make_request("GET", f"/users/{self.test_user_id}")
            
            if success and status_code == 200:
                if data["id"] == self.test_user_id and data["name"] == "Sarah Johnson":
                    self.log_test("User Retrieval", True, f"Retrieved user: {data['name']}")
                else:
                    self.log_test("User Retrieval", False, f"Data mismatch: {data}")
            else:
                self.log_test("User Retrieval", False, f"Status: {status_code}, Error: {data}")

    def test_task_management(self):
        """Test Task Management CRUD API with XP rewards"""
        print("\n📝 Testing Task Management API...")
        
        if not self.test_user_id:
            self.log_test("Task Management", False, "No test user available")
            return
        
        task_ids = []
        
        # Create multiple tasks
        tasks_to_create = [
            {"title": "Review quarterly reports", "description": "Analyze Q4 performance metrics"},
            {"title": "Prepare presentation slides", "description": "Create slides for Monday meeting"},
            {"title": "Update project documentation", "description": "Document recent API changes"}
        ]
        
        for i, task_data in enumerate(tasks_to_create):
            success, data, status_code = self.make_request("POST", f"/users/{self.test_user_id}/tasks", task_data)
            
            if success and status_code == 200:
                task_ids.append(data["id"])
                self.log_test(f"Task Creation {i+1}", True, f"Created: {data['title']}")
                
                # Verify task structure
                if data["status"] == "pending" and data["xp_earned"] == 10:
                    self.log_test(f"Task Structure {i+1}", True, "Status=pending, XP=10")
                else:
                    self.log_test(f"Task Structure {i+1}", False, f"Status={data['status']}, XP={data['xp_earned']}")
            else:
                self.log_test(f"Task Creation {i+1}", False, f"Status: {status_code}, Error: {data}")
        
        # Test task retrieval
        success, data, status_code = self.make_request("GET", f"/users/{self.test_user_id}/tasks")
        
        if success and status_code == 200:
            if len(data) >= 3:
                self.log_test("Task Retrieval", True, f"Retrieved {len(data)} tasks")
            else:
                self.log_test("Task Retrieval", False, f"Expected 3+ tasks, got {len(data)}")
        else:
            self.log_test("Task Retrieval", False, f"Status: {status_code}, Error: {data}")
        
        # Test task completion and XP rewards
        if task_ids:
            # Get user XP before completion
            success, user_before, _ = self.make_request("GET", f"/users/{self.test_user_id}")
            initial_xp = user_before.get("total_xp", 0) if success else 0
            
            # Complete first task
            update_data = {"status": "completed"}
            success, data, status_code = self.make_request("PUT", f"/users/{self.test_user_id}/tasks/{task_ids[0]}", update_data)
            
            if success and status_code == 200:
                if data["status"] == "completed" and data["completed_at"]:
                    self.log_test("Task Completion", True, f"Task completed at {data['completed_at']}")
                    
                    # Verify XP reward
                    time.sleep(1)  # Allow time for XP update
                    success, user_after, _ = self.make_request("GET", f"/users/{self.test_user_id}")
                    
                    if success:
                        new_xp = user_after.get("total_xp", 0)
                        if new_xp == initial_xp + 10:
                            self.log_test("Task XP Reward", True, f"XP increased from {initial_xp} to {new_xp}")
                        else:
                            self.log_test("Task XP Reward", False, f"Expected XP: {initial_xp + 10}, Got: {new_xp}")
                    else:
                        self.log_test("Task XP Reward", False, "Could not verify XP update")
                else:
                    self.log_test("Task Completion", False, f"Status={data['status']}, completed_at={data.get('completed_at')}")
            else:
                self.log_test("Task Completion", False, f"Status: {status_code}, Error: {data}")
        
        # Test task deletion
        if len(task_ids) > 1:
            success, data, status_code = self.make_request("DELETE", f"/users/{self.test_user_id}/tasks/{task_ids[1]}")
            
            if success and status_code == 200:
                self.log_test("Task Deletion", True, "Task deleted successfully")
            else:
                self.log_test("Task Deletion", False, f"Status: {status_code}, Error: {data}")

    def test_focus_sessions(self):
        """Test Focus Session API with XP rewards"""
        print("\n⏰ Testing Focus Session API...")
        
        if not self.test_user_id:
            self.log_test("Focus Sessions", False, "No test user available")
            return
        
        # Get user XP before session
        success, user_before, _ = self.make_request("GET", f"/users/{self.test_user_id}")
        initial_xp = user_before.get("total_xp", 0) if success else 0
        
        # Create focus session
        session_data = {
            "timer_type": "focus",
            "duration_minutes": 25
        }
        
        success, data, status_code = self.make_request("POST", f"/users/{self.test_user_id}/focus-sessions", session_data)
        
        if success and status_code == 200:
            session_id = data["id"]
            self.log_test("Focus Session Creation", True, f"Created 25-min focus session")
            
            # Verify session structure
            if data["timer_type"] == "focus" and data["duration_minutes"] == 25 and data["xp_earned"] == 25:
                self.log_test("Focus Session Structure", True, "Type=focus, Duration=25min, XP=25")
            else:
                self.log_test("Focus Session Structure", False, f"Type={data['timer_type']}, Duration={data['duration_minutes']}, XP={data['xp_earned']}")
            
            # Complete the session
            success, data, status_code = self.make_request("PUT", f"/users/{self.test_user_id}/focus-sessions/{session_id}/complete")
            
            if success and status_code == 200:
                if data["completed"] and data["completed_at"]:
                    self.log_test("Focus Session Completion", True, f"Session completed at {data['completed_at']}")
                    
                    # Verify XP reward
                    time.sleep(1)  # Allow time for XP update
                    success, user_after, _ = self.make_request("GET", f"/users/{self.test_user_id}")
                    
                    if success:
                        new_xp = user_after.get("total_xp", 0)
                        expected_xp = initial_xp + 25
                        if new_xp == expected_xp:
                            self.log_test("Focus Session XP Reward", True, f"XP increased from {initial_xp} to {new_xp}")
                        else:
                            self.log_test("Focus Session XP Reward", False, f"Expected XP: {expected_xp}, Got: {new_xp}")
                    else:
                        self.log_test("Focus Session XP Reward", False, "Could not verify XP update")
                else:
                    self.log_test("Focus Session Completion", False, f"Completed={data['completed']}, completed_at={data.get('completed_at')}")
            else:
                self.log_test("Focus Session Completion", False, f"Status: {status_code}, Error: {data}")
        else:
            self.log_test("Focus Session Creation", False, f"Status: {status_code}, Error: {data}")
        
        # Test session retrieval
        success, data, status_code = self.make_request("GET", f"/users/{self.test_user_id}/focus-sessions")
        
        if success and status_code == 200:
            if len(data) >= 1:
                self.log_test("Focus Session Retrieval", True, f"Retrieved {len(data)} sessions")
            else:
                self.log_test("Focus Session Retrieval", False, f"Expected 1+ sessions, got {len(data)}")
        else:
            self.log_test("Focus Session Retrieval", False, f"Status: {status_code}, Error: {data}")

    def test_gamification_system(self):
        """Test Gamification System - XP tracking and level calculation"""
        print("\n🎮 Testing Gamification System...")
        
        if not self.test_user_id:
            self.log_test("Gamification System", False, "No test user available")
            return
        
        # Get current user state
        success, user_data, _ = self.make_request("GET", f"/users/{self.test_user_id}")
        
        if success:
            current_xp = user_data.get("total_xp", 0)
            current_level = user_data.get("level", 1)
            
            # Test level calculation (100 XP per level)
            expected_level = max(1, (current_xp // 100) + 1)
            
            if current_level == expected_level:
                self.log_test("Level Calculation", True, f"Level {current_level} correct for {current_xp} XP")
            else:
                self.log_test("Level Calculation", False, f"Level {current_level}, expected {expected_level} for {current_xp} XP")
            
            # Test XP tracking
            if current_xp >= 35:  # Should have XP from previous tests (10 from task + 25 from session)
                self.log_test("XP Tracking", True, f"Total XP: {current_xp}")
            else:
                self.log_test("XP Tracking", False, f"Expected XP >= 35, got {current_xp}")
            
            # Test counters
            tasks_completed = user_data.get("tasks_completed", 0)
            sessions_completed = user_data.get("focus_sessions_completed", 0)
            
            if tasks_completed >= 1 and sessions_completed >= 1:
                self.log_test("Activity Counters", True, f"Tasks: {tasks_completed}, Sessions: {sessions_completed}")
            else:
                self.log_test("Activity Counters", False, f"Tasks: {tasks_completed}, Sessions: {sessions_completed}")
        else:
            self.log_test("Gamification System", False, "Could not retrieve user data")

    def test_achievement_system(self):
        """Test Achievement System - Automatic achievement unlocking"""
        print("\n🏆 Testing Achievement System...")
        
        if not self.test_user_id:
            self.log_test("Achievement System", False, "No test user available")
            return
        
        # Get current achievements
        success, achievements, status_code = self.make_request("GET", f"/users/{self.test_user_id}/achievements")
        
        if success and status_code == 200:
            self.log_test("Achievement Retrieval", True, f"Retrieved {len(achievements)} achievements")
            
            # Check if we have any achievements (we might not have enough activity yet)
            if len(achievements) > 0:
                for achievement in achievements:
                    required_fields = ["id", "achievement_type", "title", "description", "xp_reward"]
                    if all(field in achievement for field in required_fields):
                        self.log_test(f"Achievement Structure", True, f"{achievement['title']}: {achievement['description']}")
                    else:
                        self.log_test(f"Achievement Structure", False, f"Missing fields in: {achievement}")
            else:
                self.log_test("Achievement Unlocking", True, "No achievements yet (need more activity)")
        else:
            self.log_test("Achievement Retrieval", False, f"Status: {status_code}, Error: {achievements}")

    def test_dashboard_statistics(self):
        """Test Dashboard Statistics API"""
        print("\n📊 Testing Dashboard Statistics API...")
        
        if not self.test_user_id:
            self.log_test("Dashboard Statistics", False, "No test user available")
            return
        
        success, data, status_code = self.make_request("GET", f"/users/{self.test_user_id}/dashboard")
        
        if success and status_code == 200:
            # Check main structure
            required_sections = ["user", "today_stats", "level_progress", "recent_achievements", "theme"]
            
            if all(section in data for section in required_sections):
                self.log_test("Dashboard Structure", True, "All required sections present")
                
                # Test today_stats
                today_stats = data["today_stats"]
                stats_fields = ["tasks_completed", "focus_sessions_completed", "total_focus_time", "date"]
                if all(field in today_stats for field in stats_fields):
                    self.log_test("Today Stats", True, f"Tasks: {today_stats['tasks_completed']}, Sessions: {today_stats['focus_sessions_completed']}, Focus Time: {today_stats['total_focus_time']}min")
                else:
                    self.log_test("Today Stats", False, f"Missing fields in today_stats: {today_stats}")
                
                # Test level_progress
                level_progress = data["level_progress"]
                progress_fields = ["current_level", "progress_percentage", "xp_to_next_level"]
                if all(field in level_progress for field in progress_fields):
                    self.log_test("Level Progress", True, f"Level {level_progress['current_level']}, Progress: {level_progress['progress_percentage']:.1f}%")
                else:
                    self.log_test("Level Progress", False, f"Missing fields in level_progress: {level_progress}")
                
                # Test theme integration
                theme = data["theme"]
                if "name" in theme and "primary" in theme:
                    self.log_test("Dashboard Theme", True, f"Theme: {theme['name']}")
                else:
                    self.log_test("Dashboard Theme", False, f"Invalid theme data: {theme}")
            else:
                self.log_test("Dashboard Structure", False, f"Missing sections: {data.keys()}")
        else:
            self.log_test("Dashboard Statistics", False, f"Status: {status_code}, Error: {data}")

    def run_comprehensive_test(self):
        """Run all backend tests systematically"""
        print("🚀 Starting Comprehensive FocusFlow Backend API Testing")
        print("=" * 60)
        
        # Test in logical order
        self.test_api_health()
        self.test_daily_theme_api()
        self.test_user_management()
        self.test_task_management()
        self.test_focus_sessions()
        self.test_gamification_system()
        self.test_achievement_system()
        self.test_dashboard_statistics()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  • {test['test']}: {test['details']}")
        
        print(f"\n✅ Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed, total, failed_tests

if __name__ == "__main__":
    tester = FocusFlowTester()
    passed, total, failed_tests = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    exit(0 if len(failed_tests) == 0 else 1)