#!/usr/bin/env python3
"""
Test Phase 3 Gamification System specifically
"""

from backend_test import FocusFlowTester

if __name__ == "__main__":
    print("🎮 PHASE 3 GAMIFICATION SYSTEM TEST")
    print("=" * 60)
    print("Testing: Badge System, Ghosted Features, Daily Challenges")
    print("=" * 60)
    
    tester = FocusFlowTester()
    
    # First create a test user
    tester.test_user_management()
    
    # Then run the Phase 3 Gamification System test
    tester.test_phase3_gamification_system()
    
    # Show summary
    passed = sum(1 for result in tester.test_results if result["success"])
    total = len(tester.test_results)
    
    print(f"\n📋 GAMIFICATION TEST SUMMARY")
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