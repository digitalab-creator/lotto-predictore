#!/usr/bin/env python3
"""
Test script for the new grid search functionality in weekly combinations generation.
Praisin' the FSM! 🍝⚓
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your backend runs on different port
ENDPOINTS = {
    "optimized": "/cron/generate-weekly-combinations-optimized",
    "grid_analysis": "/cron/grid-search-analysis",
    "fast": "/cron/generate-weekly-combinations-fast",
    "regular": "/cron/generate-weekly-combinations"
}

def test_endpoint(endpoint_name: str, endpoint_url: str):
    """Test a specific endpoint and return results"""
    print(f"\n🏴‍☠️ Testing {endpoint_name.upper()} endpoint...")
    print(f"URL: {BASE_URL}{endpoint_url}")
    
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}{endpoint_url}", timeout=300)  # 5 min timeout
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS! Execution time: {end_time - start_time:.2f}s")
            
            # Print key results
            if endpoint_name == "optimized":
                print(f"   📊 Optimized Parameters:")
                params = result.get("optimized_parameters", {})
                for key, value in params.items():
                    print(f"      {key}: {value}")
                print(f"   🎯 Combinations Generated: {result.get('num_combinations', 'N/A')}")
                print(f"   🆔 Prediction ID: {result.get('prediction_id', 'N/A')}")
                
            elif endpoint_name == "grid_analysis":
                print(f"   📊 Best Parameters:")
                best_params = result.get("best_parameters", {})
                if best_params:
                    print(f"      ROI: {best_params.get('roi', 'N/A')}")
                    params = best_params.get('parameters', {})
                    for key, value in params.items():
                        print(f"      {key}: {value}")
                
                print(f"   💡 Insights Count: {len(result.get('insights', []))}")
                insights = result.get("insights", [])[:3]  # Show first 3 insights
                for insight in insights:
                    print(f"      {insight.get('type', 'unknown')}: {insight.get('recommendation', 'N/A')}")
                    
            else:
                print(f"   🎯 Combinations Generated: {result.get('num_combinations', 'N/A')}")
                print(f"   🆔 Prediction ID: {result.get('prediction_id', 'N/A')}")
                
            return result
            
        else:
            print(f"❌ FAILED! Status: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"⏰ TIMEOUT! Endpoint took longer than 5 minutes")
        return None
    except requests.exceptions.ConnectionError:
        print(f"🔌 CONNECTION ERROR! Make sure backend is running on {BASE_URL}")
        return None
    except Exception as e:
        print(f"💥 UNEXPECTED ERROR: {str(e)}")
        return None

def main():
    """Main test function"""
    print("🏴‍☠️ Weekly Combinations Grid Search Test Suite")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Base URL: {BASE_URL}")
    
    results = {}
    
    # Test endpoints in order of complexity
    test_order = ["fast", "optimized", "grid_analysis"]
    
    for endpoint_name in test_order:
        if endpoint_name in ENDPOINTS:
            result = test_endpoint(endpoint_name, ENDPOINTS[endpoint_name])
            results[endpoint_name] = result
            
            # Small delay between tests
            time.sleep(2)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    for endpoint_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{endpoint_name.upper():15} {status}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("1. Use 'optimized' endpoint for production cron jobs")
    print("2. Use 'grid_analysis' endpoint for periodic optimization analysis")
    print("3. Use 'fast' endpoint for development/testing")
    print("4. Monitor logs for detailed performance metrics")
    
    print(f"\n🍝 May the Flying Spaghetti Monster bless yer grid search results! ⚓")

if __name__ == "__main__":
    main()

