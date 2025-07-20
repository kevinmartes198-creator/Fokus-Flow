#!/usr/bin/env python3
"""
Focused test for TopReferralBanner API endpoints
Tests the specific APIs that the new TopReferralBanner component uses
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://cc589ab3-10bb-420b-b43d-153aab91564f.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class TopReferralBannerTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
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
        
    def make_request(self, method: str, endpoint: str, data: dict = None) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            else:
                return False, {"error": "Invalid method"}, 400
                
            return response.status_code < 400, response.json() if response.content else {}, response.status_code
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}, 0
        except json.JSONDecodeError:
            return False, {"error": "Invalid JSON response"}, response.status_code if 'response' in locals() else 0

    def test_top_referral_banner_apis(self):
        """Test all APIs that TopReferralBanner component uses"""
        print("\n🎯 TESTING TOP REFERRAL BANNER APIs")
        print("=" * 60)
        print("Testing APIs used by the new TopReferralBanner component")
        print("=" * 60)
        
        # Create a test user first
        print("\n👤 Creating test user for referral banner testing...")
        user_data = {
            "name": "Banner Test User",
            "email": "banner.test@focusflow.com"
        }
        
        success, user, status_code = self.make_request("POST", "/users", user_data)
        
        if not success or status_code != 200:
            self.log_test("User Creation for Banner Test", False, f"Status: {status_code}, Error: {user}")
            return
        
        user_id = user["id"]
        referral_code = user.get("referral_code")
        
        self.log_test("Test User Creation", True, f"Created user with referral code: {referral_code}")
        
        # TEST 1: Referral Stats API - Primary data source for TopReferralBanner
        print("\n📊 TEST 1: Referral Stats API (/users/{user_id}/referral-stats)")
        
        success, stats, status_code = self.make_request("GET", f"/users/{user_id}/referral-stats")
        
        if success and status_code == 200:
            # Check all fields that TopReferralBanner needs
            required_fields = [
                "referral_code",
                "total_referrals", 
                "total_commission_earned",
                "available_for_withdrawal",
                "referral_link",
                "earnings_breakdown"
            ]
            
            missing_fields = [field for field in required_fields if field not in stats]
            
            if not missing_fields:
                self.log_test("Referral Stats API Structure", True, "All required fields present")
                
                # Verify specific values for banner display
                if stats["referral_code"] == referral_code:
                    self.log_test("Referral Code Consistency", True, f"Code: {referral_code}")
                else:
                    self.log_test("Referral Code Consistency", False, f"Expected: {referral_code}, Got: {stats['referral_code']}")
                
                # Check earnings breakdown for banner display
                earnings = stats.get("earnings_breakdown", {})
                if earnings.get("per_referral") == 5.00:
                    self.log_test("Commission Rate Display", True, "$5.00 per referral confirmed")
                else:
                    self.log_test("Commission Rate Display", False, f"Expected $5.00, got ${earnings.get('per_referral')}")
                
                # Check referral link format
                referral_link = stats.get("referral_link", "")
                if referral_link and referral_code in referral_link:
                    self.log_test("Referral Link Format", True, f"Link contains code: {referral_link}")
                else:
                    self.log_test("Referral Link Format", False, f"Invalid link: {referral_link}")
                
                # Check initial values for new user
                if (stats["total_referrals"] == 0 and 
                    stats["total_commission_earned"] == 0.0 and
                    stats["available_for_withdrawal"] == 0.0):
                    self.log_test("Initial Banner Values", True, "New user shows $0 earnings correctly")
                else:
                    self.log_test("Initial Banner Values", False, f"Unexpected initial values: {stats}")
                    
            else:
                self.log_test("Referral Stats API Structure", False, f"Missing fields: {missing_fields}")
        else:
            self.log_test("Referral Stats API", False, f"Status: {status_code}, Error: {stats}")
        
        # TEST 2: Referral Code Validation API - For sharing functionality
        print("\n🔍 TEST 2: Referral Code Validation API (/validate-referral/{code})")
        
        success, validation, status_code = self.make_request("GET", f"/validate-referral/{referral_code}")
        
        if success and status_code == 200:
            if validation.get("valid") == True:
                # Check validation response structure for banner tooltips/modals
                required_validation_fields = ["valid", "referrer_name", "commission_amount", "message"]
                missing_validation_fields = [field for field in required_validation_fields if field not in validation]
                
                if not missing_validation_fields:
                    self.log_test("Referral Validation API Structure", True, "All validation fields present")
                    
                    if validation["commission_amount"] == 5.00:
                        self.log_test("Validation Commission Display", True, "$5.00 commission confirmed")
                    else:
                        self.log_test("Validation Commission Display", False, f"Wrong commission: ${validation['commission_amount']}")
                        
                    if validation["referrer_name"] == "Banner Test User":
                        self.log_test("Referrer Name Display", True, f"Name: {validation['referrer_name']}")
                    else:
                        self.log_test("Referrer Name Display", False, f"Wrong name: {validation['referrer_name']}")
                else:
                    self.log_test("Referral Validation API Structure", False, f"Missing fields: {missing_validation_fields}")
            else:
                self.log_test("Referral Code Validation", False, f"Code marked invalid: {validation}")
        else:
            self.log_test("Referral Code Validation API", False, f"Status: {status_code}, Error: {validation}")
        
        # TEST 3: User Dashboard API - For integrated banner display
        print("\n📋 TEST 3: User Dashboard API (/users/{user_id}/dashboard)")
        
        success, dashboard, status_code = self.make_request("GET", f"/users/{user_id}/dashboard")
        
        if success and status_code == 200:
            # Check that dashboard has user data that banner might need
            user_data = dashboard.get("user", {})
            
            if user_data:
                # Verify user data structure for banner personalization
                if user_data.get("name") == "Banner Test User":
                    self.log_test("Dashboard User Data", True, f"User name available for banner: {user_data['name']}")
                else:
                    self.log_test("Dashboard User Data", False, f"Wrong user name: {user_data.get('name')}")
                
                # Check subscription tier for banner premium features
                subscription_tier = user_data.get("subscription_tier", "free")
                if subscription_tier in ["free", "premium"]:
                    self.log_test("Subscription Tier for Banner", True, f"Tier: {subscription_tier}")
                else:
                    self.log_test("Subscription Tier for Banner", False, f"Invalid tier: {subscription_tier}")
            else:
                self.log_test("Dashboard User Data", False, "No user data in dashboard response")
        else:
            self.log_test("User Dashboard API", False, f"Status: {status_code}, Error: {dashboard}")
        
        # TEST 4: Test with Referral Activity (Create referred user)
        print("\n👥 TEST 4: Test Banner with Referral Activity")
        
        # Create a referred user to test banner with actual referral data
        referred_user_data = {
            "name": "Referred Banner User",
            "email": "referred.banner@focusflow.com",
            "referral_code": referral_code
        }
        
        success, referred_user, status_code = self.make_request("POST", "/users", referred_user_data)
        
        if success and status_code == 200:
            self.log_test("Referred User Creation", True, f"Created user with referral: {referral_code}")
            
            # Check updated referral stats after referral
            success, updated_stats, status_code = self.make_request("GET", f"/users/{user_id}/referral-stats")
            
            if success and status_code == 200:
                # Note: Referral count might still be 0 until payment is completed
                # But the API should still work correctly
                self.log_test("Updated Referral Stats", True, f"Stats API working after referral signup")
                
                # Test referral history API
                success, referral_history, status_code = self.make_request("GET", f"/users/{user_id}/referrals")
                
                if success and status_code == 200:
                    if isinstance(referral_history, list):
                        self.log_test("Referral History API", True, f"Retrieved {len(referral_history)} referral records")
                    else:
                        self.log_test("Referral History API", False, f"Expected list, got: {type(referral_history)}")
                else:
                    self.log_test("Referral History API", False, f"Status: {status_code}, Error: {referral_history}")
            else:
                self.log_test("Updated Referral Stats", False, f"Status: {status_code}, Error: {updated_stats}")
        else:
            self.log_test("Referred User Creation", False, f"Status: {status_code}, Error: {referred_user}")
        
        # TEST 5: Test Withdrawal API for banner earnings display
        print("\n💸 TEST 5: Withdrawal API for Banner Earnings")
        
        success, withdrawals, status_code = self.make_request("GET", f"/users/{user_id}/withdrawals")
        
        if success and status_code == 200:
            if isinstance(withdrawals, list):
                self.log_test("Withdrawal API for Banner", True, f"Retrieved {len(withdrawals)} withdrawal records")
                
                # Test withdrawal request API (should fail with no balance, which is expected)
                withdrawal_request = {"method": "bank_transfer"}
                success, withdrawal_response, status_code = self.make_request("POST", f"/users/{user_id}/withdraw", withdrawal_request)
                
                if status_code == 400 and "No balance available" in str(withdrawal_response):
                    self.log_test("Withdrawal Request Validation", True, "Correctly prevents withdrawal with no balance")
                elif success and status_code == 200:
                    self.log_test("Withdrawal Request Processing", True, "Withdrawal API working")
                else:
                    self.log_test("Withdrawal Request API", False, f"Status: {status_code}, Error: {withdrawal_response}")
            else:
                self.log_test("Withdrawal API for Banner", False, f"Expected list, got: {type(withdrawals)}")
        else:
            self.log_test("Withdrawal API for Banner", False, f"Status: {status_code}, Error: {withdrawals}")
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 TOP REFERRAL BANNER API TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for result in self.test_results if result["success"])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("\n✅ RESULT: TopReferralBanner APIs are WORKING CORRECTLY")
            print("The UI layout changes have NOT broken the referral system APIs.")
            print("The TopReferralBanner component will receive correct data.")
        else:
            print("\n❌ RESULT: TopReferralBanner APIs have ISSUES")
            print("Some APIs may not provide correct data for the banner component.")
        
        return success_rate >= 90

if __name__ == "__main__":
    tester = TopReferralBannerTester()
    tester.test_top_referral_banner_apis()