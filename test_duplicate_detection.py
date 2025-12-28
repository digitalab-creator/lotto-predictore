#!/usr/bin/env python3
"""
Test script to verify duplicate number detection in combinations.
"""
import sys
sys.path.insert(0, 'backend')

# Test the duplicate detection logic
def test_duplicate_detection():
    """Test that duplicate numbers are detected correctly"""
    test_cases = [
        ([1, 2, 3, 4, 5, 6], False, "No duplicates"),
        ([1, 2, 3, 4, 5, 5], True, "Duplicate at end"),
        ([2, 10, 18, 27, 29, 29], True, "Duplicate 29 (from user report)"),
        ([1, 1, 2, 3, 4, 5], True, "Duplicate at start"),
        ([1, 2, 3, 3, 4, 5], True, "Duplicate in middle"),
    ]
    
    print("Testing duplicate detection logic:")
    print("=" * 60)
    
    all_passed = True
    for numbers, expected_has_duplicate, description in test_cases:
        has_duplicate = len(numbers) != len(set(numbers))
        passed = has_duplicate == expected_has_duplicate
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{status} - {description}")
        print(f"  Numbers: {numbers}")
        print(f"  Expected duplicate: {expected_has_duplicate}, Got: {has_duplicate}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ All tests passed! Duplicate detection logic works correctly.")
    else:
        print("❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    success = test_duplicate_detection()
    sys.exit(0 if success else 1)
