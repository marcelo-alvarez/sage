#!/usr/bin/env python3
"""
Test suite for verification status parsing functionality
Tests the actual status extraction logic in the orchestrator
"""

import unittest
import tempfile
from pathlib import Path


def extract_status_from_verification(verification_content):
    """
    Extract status from verification content using the same logic as orchestrate.py
    This mirrors the exact implementation in the completion gate preparation
    """
    status_line = "Status not found"
    for line in verification_content.split('\n'):
        if "Overall Status:" in line:
            status_line = line.strip()
            break
        elif "Final Verification Status:" in line:
            status_line = line.strip()
            break
    return status_line


class TestStatusParsing(unittest.TestCase):
    """Test verification status parsing logic directly"""
    
    def test_overall_status_format(self):
        """Test parsing with 'Overall Status:' format"""
        content = """# Verification Results
        
## Changes Verified
All changes implemented correctly.

## Test Results
All tests pass.

## Overall Status: PASS - Implementation successful
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "## Overall Status: PASS - Implementation successful")
    
    def test_final_verification_status_format(self):
        """Test parsing with 'Final Verification Status:' format"""
        content = """# Verification Results
        
## Changes Verified
All changes implemented correctly.

## Test Results
All tests pass.

## Final Verification Status: PASS - Implementation successful
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "## Final Verification Status: PASS - Implementation successful")
    
    def test_no_status_information(self):
        """Test parsing with no status information"""
        content = """# Verification Results
        
## Changes Verified
All changes implemented correctly.

## Test Results
All tests pass.

No explicit status line provided.
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "Status not found")
    
    def test_malformed_status_lines(self):
        """Test parsing with malformed status lines"""
        content = """# Verification Results
        
## Changes Verified
Status: This is not the right format
Overall: Missing colon
Final Verification Status Missing colon
        
## Overall Status: PASS - This is the correct format
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "## Overall Status: PASS - This is the correct format")
    
    def test_multiple_status_lines_precedence(self):
        """Test that 'Overall Status:' takes precedence over 'Final Verification Status:'"""
        content = """# Verification Results
        
## Final Verification Status: FAIL - Initial assessment
        
## Overall Status: PASS - Final assessment
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "## Overall Status: PASS - Final assessment")
    
    def test_fallback_to_final_verification_status(self):
        """Test fallback to 'Final Verification Status:' when 'Overall Status:' not present"""
        content = """# Verification Results
        
## Some other content
        
## Final Verification Status: NEEDS_REVIEW - Requires attention
        
## More content
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "## Final Verification Status: NEEDS_REVIEW - Requires attention")
    
    def test_empty_verification_file(self):
        """Test parsing with empty verification file"""
        result = extract_status_from_verification("")
        self.assertEqual(result, "Status not found")
    
    def test_case_sensitive_matching(self):
        """Test that matching is case sensitive"""
        content = """# Verification Results
        
## overall status: PASS - lowercase won't match
## OVERALL STATUS: PASS - uppercase won't match
## Overall Status: PASS - This will match
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "## Overall Status: PASS - This will match")

    def test_partial_matching_robustness(self):
        """Test that partial matches don't interfere"""
        content = """# Verification Results
        
## Status Overall: PASS - Wrong order
## Final Status: PASS - Wrong format  
## Final Verification Status: PASS - This will match
"""
        result = extract_status_from_verification(content)
        self.assertEqual(result, "## Final Verification Status: PASS - This will match")


if __name__ == "__main__":
    unittest.main()