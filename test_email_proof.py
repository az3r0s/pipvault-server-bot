#!/usr/bin/env python3
"""
Test Email Proof System
=======================

Simple test to verify the email proof upload system works correctly.
"""

import asyncio
import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_image_upload_view():
    """Test ImageUploadView initialization"""
    try:
        # Import here to avoid event loop issues
        from views.vip_upgrade import ImageUploadView
        
        # Test view creation
        view = ImageUploadView(request_id=12345)
        
        # Verify properties
        assert view.request_id == 12345
        assert view.uploaded == False
        assert view.timeout == 1800  # 30 minutes
        
        # Check button exists
        assert len(view.children) == 1
        
        logger.info("✅ ImageUploadView test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ ImageUploadView test failed: {e}")
        return False

async def test_image_upload_modal():
    """Test ImageUploadModal initialization"""
    try:
        # Import here to avoid event loop issues
        from views.vip_upgrade import ImageUploadView, ImageUploadModal
        
        # Create a mock view
        view = ImageUploadView(request_id=12345)
        
        # Test modal creation
        modal = ImageUploadModal(request_id=12345, view=view)
        
        # Verify properties
        assert modal.request_id == 12345
        assert modal.view == view
        assert modal.title == "📸 Attach Your Screenshot"
        
        # Check text input exists
        assert len(modal.children) == 1
        
        logger.info("✅ ImageUploadModal test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ ImageUploadModal test failed: {e}")
        return False

async def run_tests():
    """Run all tests"""
    logger.info("🚀 Starting Email Proof System Tests...")
    
    tests = [
        ("ImageUploadView", test_image_upload_view),
        ("ImageUploadModal", test_image_upload_modal)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Testing {test_name}...")
        if await test_func():
            passed += 1
        else:
            logger.error(f"Test {test_name} failed!")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Email proof system is ready.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)