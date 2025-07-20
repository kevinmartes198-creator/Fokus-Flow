#!/usr/bin/env python3
"""
Daily Challenges & Kanban Board Testing for FocusFlow
Tests the newly implemented Daily Challenges API and Projects/Kanban system
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://cc589ab3-10bb-420b-b43d-153aab91564f.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class DailyChallengesKanbanTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_user_id = None
        self.project_id = None
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

    def create_test_user(self):
        """Create a test user for testing"""
        print("\n👤 Creating Test User...")
        
        # Use timestamp to ensure unique email
        timestamp = int(time.time())
        user_data = {
            "name": f"Test User {timestamp}",
            "email": f"testuser{timestamp}@focusflow.com"
        }
        
        success, data, status_code = self.make_request("POST", "/users", user_data)
        
        if success and status_code == 200:
            self.test_user_id = data["id"]
            self.log_test("Test User Creation", True, f"Created user: {data['name']} (ID: {data['id'][:8]}...)")
            return True
        else:
            self.log_test("Test User Creation", False, f"Status: {status_code}, Error: {data}")
            return False

    def test_daily_challenges_api(self):
        """🎮 Test Daily Challenges API endpoints - Previously failing"""
        print("\n🎮 Testing Daily Challenges API...")
        
        # STEP 1: Test GET /api/gamification/daily-challenges
        print("\n📋 STEP 1: Test Daily Challenges Retrieval")
        success, challenges_data, status_code = self.make_request("GET", "/gamification/daily-challenges")
        
        if success and status_code == 200:
            # Verify challenges structure
            expected_challenges = ["focus_master", "task_crusher", "streak_warrior", "theme_explorer", "early_bird"]
            
            if all(challenge in challenges_data for challenge in expected_challenges):
                self.log_test("Daily Challenges API", True, f"Retrieved {len(challenges_data)} challenges")
                
                # Verify challenge structure
                for challenge_id, challenge in challenges_data.items():
                    required_fields = ["name", "description", "icon", "goal", "type", "reward", "difficulty"]
                    if all(field in challenge for field in required_fields):
                        self.log_test(f"Challenge Structure ({challenge_id})", True, f"{challenge['name']}: {challenge['description']}")
                    else:
                        self.log_test(f"Challenge Structure ({challenge_id})", False, f"Missing fields: {challenge}")
            else:
                self.log_test("Daily Challenges API", False, f"Missing expected challenges: {challenges_data.keys()}")
        else:
            self.log_test("Daily Challenges API", False, f"Status: {status_code}, Error: {challenges_data}")
            return
        
        # STEP 2: Test GET /api/users/{user_id}/daily-challenges
        if not self.test_user_id:
            self.log_test("User Daily Challenges", False, "No test user available")
            return
            
        print("\n👤 STEP 2: Test User Daily Challenge Progress")
        success, user_challenges, status_code = self.make_request("GET", f"/users/{self.test_user_id}/daily-challenges")
        
        if success and status_code == 200:
            if isinstance(user_challenges, list):
                self.log_test("User Daily Challenges API", True, f"Retrieved {len(user_challenges)} challenge statuses")
                
                # Verify user challenge structure
                if len(user_challenges) > 0:
                    challenge = user_challenges[0]
                    required_fields = ["challenge_id", "name", "description", "current_progress", "goal", "completed"]
                    if all(field in challenge for field in required_fields):
                        self.log_test("User Challenge Structure", True, f"Progress: {challenge['current_progress']}/{challenge['goal']}")
                    else:
                        self.log_test("User Challenge Structure", False, f"Missing fields: {challenge}")
                else:
                    self.log_test("User Challenge Progress", True, "No progress yet (expected for new user)")
            else:
                self.log_test("User Daily Challenges API", False, f"Expected list, got: {type(user_challenges)}")
        else:
            self.log_test("User Daily Challenges API", False, f"Status: {status_code}, Error: {user_challenges}")

    def test_projects_kanban_system(self):
        """📋 Test Projects & Kanban Board System - End-to-end workflow"""
        print("\n📋 Testing Projects & Kanban Board System...")
        
        if not self.test_user_id:
            self.log_test("Projects & Kanban System", False, "No test user available")
            return
        
        # STEP 1: Test GET /api/users/{user_id}/projects (should be empty initially)
        print("\n📁 STEP 1: Test User Projects Retrieval")
        success, projects, status_code = self.make_request("GET", f"/users/{self.test_user_id}/projects")
        
        if success and status_code == 200:
            if isinstance(projects, list):
                self.log_test("User Projects Retrieval", True, f"Retrieved {len(projects)} projects")
            else:
                self.log_test("User Projects Retrieval", False, f"Expected list, got: {type(projects)}")
        else:
            self.log_test("User Projects Retrieval", False, f"Status: {status_code}, Error: {projects}")
            return
        
        # STEP 2: Test POST /api/users/{user_id}/projects (create project)
        print("\n➕ STEP 2: Test Project Creation")
        project_data = {
            "name": "Website Redesign Project",
            "description": "Complete redesign of company website with modern UI/UX",
            "color": "blue"
        }
        
        success, project, status_code = self.make_request("POST", f"/users/{self.test_user_id}/projects", project_data)
        
        if success and status_code == 200:
            project_id = project.get("id")
            if project_id:
                self.project_id = project_id  # Store for later tests
                self.log_test("Project Creation", True, f"Created project: {project['name']} (ID: {project_id[:8]}...)")
                
                # Verify project structure
                required_fields = ["id", "user_id", "name", "description", "color", "status", "created_at"]
                if all(field in project for field in required_fields):
                    self.log_test("Project Structure", True, f"Status: {project['status']}, Color: {project['color']}")
                else:
                    self.log_test("Project Structure", False, f"Missing fields: {project}")
            else:
                self.log_test("Project Creation", False, "Missing project ID")
                return
        else:
            self.log_test("Project Creation", False, f"Status: {status_code}, Error: {project}")
            return
        
        # STEP 3: Test GET /api/projects/{project_id}/kanban (get kanban board)
        print("\n📊 STEP 3: Test Kanban Board Retrieval")
        success, kanban_board, status_code = self.make_request("GET", f"/projects/{project_id}/kanban")
        
        if success and status_code == 200:
            # Verify kanban board structure
            required_fields = ["project", "board", "task_count", "todo_count", "in_progress_count", "done_count"]
            if all(field in kanban_board for field in required_fields):
                board = kanban_board["board"]
                if all(column in board for column in ["todo", "in_progress", "done"]):
                    self.log_test("Kanban Board Structure", True, f"Tasks: {kanban_board['task_count']}, Todo: {kanban_board['todo_count']}")
                else:
                    self.log_test("Kanban Board Structure", False, f"Missing columns: {board.keys()}")
            else:
                self.log_test("Kanban Board Structure", False, f"Missing fields: {kanban_board}")
        else:
            self.log_test("Kanban Board Retrieval", False, f"Status: {status_code}, Error: {kanban_board}")
            return
        
        # STEP 4: Test POST /api/projects/{project_id}/tasks (create kanban tasks)
        print("\n📝 STEP 4: Test Kanban Task Creation")
        
        tasks_to_create = [
            {
                "title": "Design wireframes",
                "description": "Create low-fidelity wireframes for all main pages",
                "project_id": project_id,
                "priority": "high"
            },
            {
                "title": "Set up development environment",
                "description": "Configure local development setup with latest frameworks",
                "project_id": project_id,
                "priority": "medium"
            },
            {
                "title": "Content audit",
                "description": "Review and categorize existing website content",
                "project_id": project_id,
                "priority": "low"
            }
        ]
        
        created_task_ids = []
        
        for i, task_data in enumerate(tasks_to_create):
            success, task, status_code = self.make_request("POST", f"/projects/{project_id}/tasks", task_data)
            
            if success and status_code == 200:
                task_id = task.get("id")
                if task_id:
                    created_task_ids.append(task_id)
                    self.log_test(f"Kanban Task Creation {i+1}", True, f"Created: {task['title']}")
                    
                    # Verify task structure
                    required_fields = ["id", "user_id", "project_id", "title", "column", "position", "priority"]
                    if all(field in task for field in required_fields):
                        if task["column"] == "todo" and task["project_id"] == project_id:
                            self.log_test(f"Kanban Task Structure {i+1}", True, f"Column: {task['column']}, Priority: {task['priority']}")
                        else:
                            self.log_test(f"Kanban Task Structure {i+1}", False, f"Wrong column/project: {task['column']}, {task['project_id']}")
                    else:
                        self.log_test(f"Kanban Task Structure {i+1}", False, f"Missing fields: {task}")
                else:
                    self.log_test(f"Kanban Task Creation {i+1}", False, "Missing task ID")
            else:
                self.log_test(f"Kanban Task Creation {i+1}", False, f"Status: {status_code}, Error: {task}")
        
        if len(created_task_ids) == 0:
            self.log_test("Kanban Task Movement", False, "No tasks created for movement testing")
            return
        
        # STEP 5: Test Kanban board with tasks
        print("\n📊 STEP 5: Test Kanban Board with Tasks")
        success, updated_board, status_code = self.make_request("GET", f"/projects/{project_id}/kanban")
        
        if success and status_code == 200:
            if updated_board["task_count"] == len(created_task_ids):
                self.log_test("Kanban Board Task Count", True, f"Board shows {updated_board['task_count']} tasks")
                
                # Verify all tasks are in todo column
                if updated_board["todo_count"] == len(created_task_ids) and updated_board["in_progress_count"] == 0:
                    self.log_test("Initial Task Placement", True, f"All {len(created_task_ids)} tasks in todo column")
                else:
                    self.log_test("Initial Task Placement", False, f"Todo: {updated_board['todo_count']}, In Progress: {updated_board['in_progress_count']}")
            else:
                self.log_test("Kanban Board Task Count", False, f"Expected {len(created_task_ids)}, got {updated_board['task_count']}")
        else:
            self.log_test("Kanban Board with Tasks", False, f"Status: {status_code}, Error: {updated_board}")
        
        # STEP 6: Test PUT /api/tasks/kanban/{task_id}/move (move tasks between columns)
        print("\n🔄 STEP 6: Test Task Movement Between Columns")
        
        if len(created_task_ids) >= 2:
            # Get user XP before task completion
            success, user_before, _ = self.make_request("GET", f"/users/{self.test_user_id}")
            initial_xp = user_before.get("total_xp", 0) if success else 0
            
            # Move first task to in_progress
            move_data = {"column": "in_progress", "position": 0}
            success, move_response, status_code = self.make_request("PUT", f"/tasks/kanban/{created_task_ids[0]}/move", move_data)
            
            if success and status_code == 200:
                self.log_test("Task Move to In Progress", True, "Task moved to in_progress column")
                
                # Move second task to done (should award XP)
                move_data = {"column": "done", "position": 0}
                success, move_response, status_code = self.make_request("PUT", f"/tasks/kanban/{created_task_ids[1]}/move", move_data)
                
                if success and status_code == 200:
                    self.log_test("Task Move to Done", True, "Task moved to done column")
                    
                    # Verify XP reward for task completion
                    time.sleep(1)  # Allow time for XP update
                    success, user_after, _ = self.make_request("GET", f"/users/{self.test_user_id}")
                    
                    if success:
                        new_xp = user_after.get("total_xp", 0)
                        xp_gained = new_xp - initial_xp
                        
                        # Should get 15 XP base + potential premium bonus
                        expected_base_xp = 15
                        subscription_tier = user_after.get("subscription_tier", "free")
                        
                        if subscription_tier == "free":
                            expected_xp = expected_base_xp
                        else:
                            expected_xp = expected_base_xp + int(expected_base_xp * 0.2)  # 20% premium bonus
                        
                        if xp_gained == expected_xp:
                            self.log_test("Kanban Task Completion XP", True, f"Gained {xp_gained} XP for task completion")
                        else:
                            self.log_test("Kanban Task Completion XP", False, f"Expected {expected_xp} XP, got {xp_gained}")
                    else:
                        self.log_test("Kanban Task Completion XP", False, "Could not verify XP update")
                else:
                    self.log_test("Task Move to Done", False, f"Status: {status_code}, Error: {move_response}")
            else:
                self.log_test("Task Move to In Progress", False, f"Status: {status_code}, Error: {move_response}")
        
        # STEP 7: Verify final board state
        print("\n✅ STEP 7: Verify Final Board State")
        success, final_board, status_code = self.make_request("GET", f"/projects/{project_id}/kanban")
        
        if success and status_code == 200:
            todo_count = final_board["todo_count"]
            in_progress_count = final_board["in_progress_count"]
            done_count = final_board["done_count"]
            
            # Should have: 1 in todo, 1 in progress, 1 in done (if we moved 2 tasks)
            if len(created_task_ids) >= 2:
                expected_distribution = f"Todo: {len(created_task_ids)-2}, In Progress: 1, Done: 1"
                actual_distribution = f"Todo: {todo_count}, In Progress: {in_progress_count}, Done: {done_count}"
                
                if in_progress_count == 1 and done_count == 1:
                    self.log_test("Final Board State", True, f"Correct distribution - {actual_distribution}")
                else:
                    self.log_test("Final Board State", False, f"Expected {expected_distribution}, got {actual_distribution}")
            else:
                self.log_test("Final Board State", True, f"Board state: {actual_distribution}")
        else:
            self.log_test("Final Board State", False, f"Status: {status_code}, Error: {final_board}")

    def run_complete_test(self):
        """Run complete Daily Challenges and Kanban test suite"""
        print("🎯 DAILY CHALLENGES & KANBAN BOARD TESTING")
        print("=" * 60)
        print("PRIMARY FOCUS: Testing newly implemented Daily Challenges API and Projects/Kanban system")
        print("=" * 60)
        
        # Create test user first
        if not self.create_test_user():
            print("❌ Cannot proceed without test user")
            return
        
        # Test Daily Challenges API (previously failing)
        print("\n" + "🎮" * 20)
        print("TESTING DAILY CHALLENGES API (Previously Failing)")
        print("🎮" * 20)
        self.test_daily_challenges_api()
        
        # Test Projects & Kanban System (newly implemented)
        print("\n" + "📋" * 20)
        print("TESTING PROJECTS & KANBAN BOARD SYSTEM (Newly Implemented)")
        print("📋" * 20)
        self.test_projects_kanban_system()
        
        # Print summary
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📋 DAILY CHALLENGES & KANBAN TEST SUMMARY")
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
        
        # Show Daily Challenges specific results
        daily_challenges_tests = [result for result in self.test_results if any(keyword in result["test"].lower() 
                                for keyword in ["daily", "challenge"])]
        
        if daily_challenges_tests:
            dc_passed = sum(1 for test in daily_challenges_tests if test["success"])
            print(f"\n🎮 DAILY CHALLENGES RESULTS:")
            print(f"Daily Challenges Tests: {len(daily_challenges_tests)}")
            print(f"Daily Challenges Passed: {dc_passed}")
            print(f"Daily Challenges Success Rate: {(dc_passed/len(daily_challenges_tests))*100:.1f}%")
        
        # Show Kanban specific results
        kanban_tests = [result for result in self.test_results if any(keyword in result["test"].lower() 
                       for keyword in ["kanban", "project", "task creation", "task move", "board"])]
        
        if kanban_tests:
            kanban_passed = sum(1 for test in kanban_tests if test["success"])
            print(f"\n📋 KANBAN BOARD RESULTS:")
            print(f"Kanban Tests: {len(kanban_tests)}")
            print(f"Kanban Passed: {kanban_passed}")
            print(f"Kanban Success Rate: {(kanban_passed/len(kanban_tests))*100:.1f}%")
        
        # Success criteria assessment
        print(f"\n🎯 SUCCESS CRITERIA ASSESSMENT:")
        
        # Daily Challenges criteria
        dc_api_working = any("Daily Challenges API" in test["test"] and test["success"] for test in self.test_results)
        user_dc_working = any("User Daily Challenges API" in test["test"] and test["success"] for test in self.test_results)
        
        print(f"✅ Daily Challenges API Working: {'YES' if dc_api_working else 'NO'}")
        print(f"✅ User Daily Challenges API Working: {'YES' if user_dc_working else 'NO'}")
        
        # Kanban criteria
        project_creation = any("Project Creation" in test["test"] and test["success"] for test in self.test_results)
        kanban_board = any("Kanban Board Structure" in test["test"] and test["success"] for test in self.test_results)
        task_creation = any("Kanban Task Creation" in test["test"] and test["success"] for test in self.test_results)
        task_movement = any("Task Move" in test["test"] and test["success"] for test in self.test_results)
        xp_rewards = any("Kanban Task Completion XP" in test["test"] and test["success"] for test in self.test_results)
        
        print(f"✅ Project Creation Working: {'YES' if project_creation else 'NO'}")
        print(f"✅ Kanban Board Retrieval Working: {'YES' if kanban_board else 'NO'}")
        print(f"✅ Kanban Task Creation Working: {'YES' if task_creation else 'NO'}")
        print(f"✅ Task Movement Working: {'YES' if task_movement else 'NO'}")
        print(f"✅ XP Rewards for Task Completion: {'YES' if xp_rewards else 'NO'}")
        
        # Overall assessment
        critical_features_working = sum([dc_api_working, user_dc_working, project_creation, kanban_board, task_creation, task_movement])
        
        print(f"\n🏆 OVERALL ASSESSMENT:")
        print(f"Critical Features Working: {critical_features_working}/6")
        
        if critical_features_working >= 5:
            print("🎉 SUCCESS: Daily Challenges and Kanban system are working!")
        elif critical_features_working >= 3:
            print("⚠️  PARTIAL SUCCESS: Most features working, some issues need attention")
        else:
            print("❌ NEEDS WORK: Major issues found, requires fixes")
        
        print(f"\n✅ Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed, total, failed_tests

if __name__ == "__main__":
    tester = DailyChallengesKanbanTester()
    tester.run_complete_test()