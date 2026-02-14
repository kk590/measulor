"""
Keygen.sh License Integration for Measulor
This module provides license validation using Keygen API
"""
import os
import requests
from datetime import datetime, timedelta
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Keygen Configuration
KEYGEN_ACCOUNT_ID = os.getenv('KEYGEN_ACCOUNT_ID')
KEYGEN_PRODUCT_ID = os.getenv('KEYGEN_PRODUCT_ID')
KEYGEN_PRODUCT_TOKEN = os.getenv('KEYGEN_PRODUCT_TOKEN')

# Validate required environment variables
required_vars = ['KEYGEN_ACCOUNT_ID', 'KEYGEN_PRODUCT_ID', 'KEYGEN_PRODUCT_TOKEN']
for var in required_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        raise EnvironmentError(f"Missing required environment variable: {var}")

KEYGEN_API_URL = f'https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT_ID}/licenses'

# License cache (in-memory with TTL)
license_cache = {}
CACHE_TTL = timedelta(minutes=5)

def verify_license_with_keygen(license_key):
    """
    Verify license key with Keygen API
    Returns: (is_valid, license_data)
    """
    
    # Check cache first
    if license_key in license_cache:
        cached_data = license_cache[license_key]
        cache_time = cached_data.get('cached_at', datetime.min)
        if datetime.now() - cache_time < CACHE_TTL:
            logger.info(f"Cache hit for license: {license_key}")
            return cached_data.get('valid', False), cached_data.get('data', {})
    
    # Validate with Keygen API
    url = f'https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT_ID}/licenses/actions/validate-key'
    
    headers = {
        'Content-Type': 'application/vnd.api+json; charset=utf-8',
        'Accept': 'application/vnd.api+json; charset=utf-8',
        'Authorization': f'Bearer {KEYGEN_PRODUCT_TOKEN}'
    }
    
    logger.info(f"Validating license key: {license_key}")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={
                'meta': {
                    'key': license_key,
                    'scope': {
                        'product': KEYGEN_PRODUCT_ID
                    }
                }
            },
            timeout=10  # 10 second timeout
        )
        
        logger.info(f"Keygen API Response Status: {response.status_code}")
        logger.info(f"Keygen API Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            is_valid = data.get('meta', {}).get('valid', False)
            
            # Cache the result
            license_cache[license_key] = {
                'valid': is_valid,
                'data': data,
                'cached_at': datetime.now()
            }
            
            logger.info(f"License {license_key} is {'valid' if is_valid else 'invalid'}")
            return is_valid, data
        elif response.status_code == 404:
            logger.warning(f"License key not found: {license_key}")
            return False, {}
        elif response.status_code == 401:
            logger.error("Unauthorized: Check KEYGEN_PRODUCT_TOKEN")
            return False, {}
        else:
            logger.error(f"Keygen validation failed with status {response.status_code}: {response.text}")
            return False, {}
    
    except requests.Timeout:
        logger.error("Keygen API timeout after 10 seconds")
        return False, {}
    
    except Exception as e:
        logger.error(f"Error validating license: {str(e)}", exc_info=True)
        return False, {}


def clear_cache():
    """
    Clear the license cache
    """
    global license_cache
    license_cache.clear()
    logger.info("License cache cleared")


def get_cache_stats():
    """
    Get cache statistics
    """
    return {
        'cache_size': len(license_cache),
        'cache_items': list(license_cache.keys())
    }

# Health check function

def check_health():
    """
    Check if Keygen integration is configured correctly
    """
    return {
        'configured': all(os.getenv(var) for var in required_vars),
        'account_id': KEYGEN_ACCOUNT_ID,
        'product_id': KEYGEN_PRODUCT_ID,
        'has_token': bool(KEYGEN_PRODUCT_TOKEN)
    }
