#!/usr/bin/env python3
"""
Quick verification test for core APIs after UI layout changes
Tests dashboard, user management, tasks, focus sessions, and achievements
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://cc589ab3-10bb-420b-b43d-153aab91564f.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class CoreAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_results = []
        self.test_user_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def make_request(self, method: str, endpoint: str, data: dict = None) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=10)
            else:
                return False, {"error": "Invalid method"}, 400
                
            return response.status_code < 400, response.json() if response.content else {}, response.status_code
        except Exception as e:
            return False, {"error": str(e)}, 0

    def test_core_apis_after_ui_changes(self):
        """Test core APIs to ensure UI layout changes haven't broken backend functionality"""
        print("\n🔍 TESTING CORE APIs AFTER UI LAYOUT CHANGES")
        print("=" * 70)
        print("Verifying that TopReferralBanner UI changes haven't broken existing APIs")
        print("=" * 70)
        
        # Test 1: API Health Check
        print("\n🏥 TEST 1: API Health Check")
        success, data, status_code = self.make_request("GET", "/")
        
        if success and status_code == 200:
            self.log_test("API Health Check", True, f"API running: {data.get('message', 'OK')}")
        else:
            self.log_test("API Health Check", False, f"Status: {status_code}")
            return False
        
        # Test 2: User Management APIs
        print("\n👤 TEST 2: User Management APIs")
        
        # Create user
        user_data = {
            "name": "UI Test User",
            "email": "ui.test@focusflow.com"
        }
        
        success, user, status_code = self.make_request("POST", "/users", user_data)
        
        if success and status_code == 200:
            self.test_user_id = user["id"]
            self.log_test("User Creation", True, f"Created user: {user['name']}")
            
            # Test user retrieval
            success, retrieved_user, status_code = self.make_request("GET", f"/users/{self.test_user_id}")
            
            if success and status_code == 200:
                self.log_test("User Retrieval", True, f"Retrieved: {retrieved_user['name']}")
            else:
                self.log_test("User Retrieval", False, f"Status: {status_code}")
        else:
            self.log_test("User Creation", False, f"Status: {status_code}")
            return False
        
        # Test 3: Dashboard API (Critical for UI layout)
        print("\n📊 TEST 3: Dashboard API (Used by modified UI)")
        
        success, dashboard, status_code = self.make_request("GET", f"/users/{self.test_user_id}/dashboard")
        
        if success and status_code == 200:
            # Check all sections that the modified UI needs
            required_sections = ["user", "today_stats", "level_progress", "theme", "premium_features"]
            missing_sections = [section for section in required_sections if section not in dashboard]
            
            if not missing_sections:
                self.log_test("Dashboard API Structure", True, "All UI sections present")
                
                # Check theme data (important for UI styling)
                theme = dashboard.get("theme", {})
                if theme.get("name") and theme.get("primary"):
                    self.log_test("Dashboard Theme Data", True, f"Theme: {theme['name']}")
                else:
                    self.log_test("Dashboard Theme Data", False, f"Invalid theme: {theme}")
                
                # Check premium features (important for UI feature flags)
                premium_features = dashboard.get("premium_features", {})
                if isinstance(premium_features, dict):
                    self.log_test("Premium Features Data", True, f"Features available for UI")
                else:
                    self.log_test("Premium Features Data", False, f"Invalid features: {premium_features}")
            else:
                self.log_test("Dashboard API Structure", False, f"Missing sections: {missing_sections}")
        else:
            self.log_test("Dashboard API", False, f"Status: {status_code}")
        
        # Test 4: Task Management APIs
        print("\n📝 TEST 4: Task Management APIs")
        
        # Create task
        task_data = {
            "title": "UI Layout Test Task",
            "description": "Testing task API after UI changes"
        }
        
        success, task, status_code = self.make_request("POST", f"/users/{self.test_user_id}/tasks", task_data)
        
        if success and status_code == 200:
            task_id = task["id"]
            self.log_test("Task Creation", True, f"Created: {task['title']}")
            
            # Test task completion and XP
            initial_xp = 0
            success, user_before, _ = self.make_request("GET", f"/users/{self.test_user_id}")
            if success:
                initial_xp = user_before.get("total_xp", 0)
            
            # Complete task
            success, completed_task, status_code = self.make_request("PUT", f"/users/{self.test_user_id}/tasks/{task_id}", {"status": "completed"})
            
            if success and status_code == 200:
                self.log_test("Task Completion", True, "Task completed successfully")
                
                # Verify XP reward
                time.sleep(1)
                success, user_after, _ = self.make_request("GET", f"/users/{self.test_user_id}")
                if success:
                    new_xp = user_after.get("total_xp", 0)
                    if new_xp > initial_xp:
                        self.log_test("Task XP Reward", True, f"XP increased: {initial_xp} → {new_xp}")
                    else:
                        self.log_test("Task XP Reward", False, f"XP not increased: {initial_xp} → {new_xp}")
            else:
                self.log_test("Task Completion", False, f"Status: {status_code}")
        else:
            self.log_test("Task Creation", False, f"Status: {status_code}")
        
        # Test 5: Focus Session APIs
        print("\n⏰ TEST 5: Focus Session APIs")
        
        # Create focus session
        session_data = {
            "timer_type": "focus",
            "duration_minutes": 25
        }
        
        success, session, status_code = self.make_request("POST", f"/users/{self.test_user_id}/focus-sessions", session_data)
        
        if success and status_code == 200:
            session_id = session["id"]
            self.log_test("Focus Session Creation", True, f"Created 25-min session")
            
            # Complete session
            success, completed_session, status_code = self.make_request("PUT", f"/users/{self.test_user_id}/focus-sessions/{session_id}/complete")
            
            if success and status_code == 200:
                self.log_test("Focus Session Completion", True, "Session completed successfully")
            else:
                self.log_test("Focus Session Completion", False, f"Status: {status_code}")
        else:
            self.log_test("Focus Session Creation", False, f"Status: {status_code}")
        
        # Test 6: Achievement System
        print("\n🏆 TEST 6: Achievement System")
        
        success, achievements, status_code = self.make_request("GET", f"/users/{self.test_user_id}/achievements")
        
        if success and status_code == 200:
            if isinstance(achievements, list):
                self.log_test("Achievement System", True, f"Retrieved {len(achievements)} achievements")
            else:
                self.log_test("Achievement System", False, f"Expected list, got: {type(achievements)}")
        else:
            self.log_test("Achievement System", False, f"Status: {status_code}")
        
        # Test 7: Theme API (Used by UI)
        print("\n🎨 TEST 7: Theme API")
        
        success, theme, status_code = self.make_request("GET", "/theme")
        
        if success and status_code == 200:
            if theme.get("name") and theme.get("primary"):
                self.log_test("Theme API", True, f"Theme: {theme['name']}")
            else:
                self.log_test("Theme API", False, f"Invalid theme data: {theme}")
        else:
            self.log_test("Theme API", False, f"Status: {status_code}")
        
        # Test 8: Subscription Package API (For premium features)
        print("\n💳 TEST 8: Subscription Package API")
        
        success, packages, status_code = self.make_request("GET", "/subscription/packages")
        
        if success and status_code == 200:
            if "monthly_premium" in packages:
                package = packages["monthly_premium"]
                if package.get("amount") == 9.99:
                    self.log_test("Subscription Packages", True, f"Premium: ${package['amount']}")
                else:
                    self.log_test("Subscription Packages", False, f"Wrong price: ${package.get('amount')}")
            else:
                self.log_test("Subscription Packages", False, "Missing monthly_premium package")
        else:
            self.log_test("Subscription Packages", False, f"Status: {status_code}")
        
        # Summary
        print("\n" + "=" * 70)
        print("🎯 CORE API VERIFICATION SUMMARY")
        print("=" * 70)
        
        passed_tests = sum(1 for result in self.test_results if result["success"])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("\n✅ RESULT: Core APIs are WORKING CORRECTLY after UI layout changes")
            print("The TopReferralBanner implementation has NOT broken existing functionality.")
        else:
            print("\n❌ RESULT: Some core APIs have ISSUES after UI layout changes")
            print("The UI layout changes may have affected backend functionality.")
        
        return success_rate >= 90

if __name__ == "__main__":
    tester = CoreAPITester()
    tester.test_core_apis_after_ui_changes()