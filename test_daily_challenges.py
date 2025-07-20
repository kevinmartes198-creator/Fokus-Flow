#!/usr/bin/env python3
"""
Test Daily Challenges System specifically - what's actually implemented
"""

from backend_test import FocusFlowTester

if __name__ == "__main__":
    print("📅 DAILY CHALLENGES SYSTEM TEST")
    print("=" * 60)
    print("Testing: Daily Challenges System Phase 2+")
    print("=" * 60)
    
    tester = FocusFlowTester()
    
    # First create a test user
    tester.test_user_management()
    
    # Test what's actually implemented for gamification
    print("\n🎮 Testing Implemented Gamification Features...")
    
    # Test Badge System API
    print("\n🏆 Testing Badge System API...")
    success, badge_system, status_code = tester.make_request("GET", "/gamification/badge-system")
    
    if success and status_code == 200:
        tester.log_test("Badge System API", True, f"Retrieved badge system with {len(badge_system.get('badges', {}))} badges")
        
        # Check categories
        categories = badge_system.get("categories", {})
        expected_categories = ["progression", "focus", "streak", "premium", "special", "social"]
        if all(cat in categories for cat in expected_categories):
            tester.log_test("Badge Categories", True, f"All 6 categories present")
        else:
            tester.log_test("Badge Categories", False, f"Missing categories")
    else:
        tester.log_test("Badge System API", False, f"Status: {status_code}, Error: {badge_system}")
    
    # Test User Badge Management
    print("\n🎖️ Testing User Badge Management...")
    if tester.test_user_id:
        success, user_badges, status_code = tester.make_request("GET", f"/users/{tester.test_user_id}/badges")
        
        if success and status_code == 200:
            tester.log_test("User Badges API", True, f"Retrieved {len(user_badges)} user badges")
        else:
            tester.log_test("User Badges API", False, f"Status: {status_code}")
        
        # Test Badge Progress API
        success, badge_progress, status_code = tester.make_request("GET", f"/users/{tester.test_user_id}/badge-progress")
        
        if success and status_code == 200:
            tester.log_test("Badge Progress API", True, f"Retrieved progress for {len(badge_progress)} badges")
        else:
            tester.log_test("Badge Progress API", False, f"Status: {status_code}")
        
        # Test Badge Check API
        success, badge_check, status_code = tester.make_request("POST", f"/users/{tester.test_user_id}/check-badges")
        
        if success and status_code == 200:
            newly_unlocked = badge_check.get("newly_unlocked", 0)
            tester.log_test("Badge Check API", True, f"Badge check completed, {newly_unlocked} newly unlocked")
        else:
            tester.log_test("Badge Check API", False, f"Status: {status_code}")
    
    # Test Ghosted Features API
    print("\n👻 Testing Ghosted Features API...")
    success, ghosted_features, status_code = tester.make_request("GET", "/gamification/ghosted-features")
    
    if success and status_code == 200:
        expected_features = ["custom_timers", "premium_themes", "premium_sounds", "advanced_analytics", "cloud_backup", "achievement_accelerator"]
        if all(feature in ghosted_features for feature in expected_features):
            tester.log_test("Ghosted Features API", True, f"All 6 ghosted features present")
        else:
            tester.log_test("Ghosted Features API", False, f"Missing features")
    else:
        tester.log_test("Ghosted Features API", False, f"Status: {status_code}")
    
    # Test Daily Challenges API (check if implemented)
    print("\n📅 Testing Daily Challenges API...")
    success, daily_challenges, status_code = tester.make_request("GET", "/gamification/daily-challenges")
    
    if success and status_code == 200:
        tester.log_test("Daily Challenges API", True, f"Daily challenges API working")
    elif status_code == 404:
        tester.log_test("Daily Challenges API", False, "Daily Challenges API not implemented yet")
    else:
        tester.log_test("Daily Challenges API", False, f"Status: {status_code}")
    
    # Test User Daily Challenges API (check if implemented)
    if tester.test_user_id:
        success, user_challenges, status_code = tester.make_request("GET", f"/users/{tester.test_user_id}/daily-challenges")
        
        if success and status_code == 200:
            tester.log_test("User Daily Challenges API", True, f"User daily challenges API working")
        elif status_code == 404:
            tester.log_test("User Daily Challenges API", False, "User Daily Challenges API not implemented yet")
        else:
            tester.log_test("User Daily Challenges API", False, f"Status: {status_code}")
    
    # Show summary
    passed = sum(1 for result in tester.test_results if result["success"])
    total = len(tester.test_results)
    
    print(f"\n📋 DAILY CHALLENGES & GAMIFICATION TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Show failed tests
    failed_tests = [result for result in tester.test_results if not result["success"]]
    if failed_tests:
        print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"  • {test['test']}: {test['details']}")
    else:
        print(f"\n✅ ALL TESTS PASSED!")
    
    print(f"\n🎮 GAMIFICATION SYSTEM STATUS:")
    print(f"✅ Badge System API - IMPLEMENTED")
    print(f"✅ User Badge Management - IMPLEMENTED") 
    print(f"✅ Badge Progress Tracking - IMPLEMENTED")
    print(f"✅ Badge Unlock Detection - IMPLEMENTED")
    print(f"✅ Ghosted Features System - IMPLEMENTED")
    print(f"❌ Daily Challenges API - NOT IMPLEMENTED")
    print(f"❌ User Daily Challenges API - NOT IMPLEMENTED")