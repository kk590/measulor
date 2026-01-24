"""
Keygen.sh License Integration for Measulor
This module provides license validation using Keygen API
"""

import os
import requests
from datetime import datetime, timedelta

# Keygen Configuration
KEY GEN_ACCOUNT_ID = os.getenv('KEYGEN_ACCOUNT_ID', '51bb33ef-d469-4c06-ac4b-68b65ce1c647')
KEYGEN_PRODUCT_TOKEN = os.getenv('KEYGEN_PRODUCT_TOKEN', 'prod-baddb474348d6ab89817af26148cf1468759')
KEYGEN_API_URL = 'https://api.keygen.sh/v1/accounts/{}/licenses'.format(KEYGEN_ACCOUNT_ID)

# License cache (in-memory)
license_cache = {}

def verify_license_with_keygen(license_key):
    """
    Verify license key with Keygen API
    Returns: (is_valid, license_data)
    """
    try:
        # Check cache first (5 minutes TTL)
        if license_key in license_cache:
            cached_data = license_cache[license_key]
            cache_time = cached_data.get('cached_at', datetime.min)
            if datetime.now() - cache_time < timedelta(minutes=5):
                return cached_data.get('valid', False), cached_data.get('data', {})
        
        # Validate with Keygen API
        url = f'https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT_ID}/licenses/{license_key}/actions/validate'
        
        headers = {
            'Authorization': f'Bearer {KEYGEN_PRODUCT_TOKEN}',
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json'
        }
        
        response = requests.post(url, headers=headers, json={
            'meta': {
                'scope': {
                    'product': '932d3cfd-d7f4-4e46-b0be-09123e06bc19'  # Measulor Product ID
                }
            }
        })
        
        if response.status_code == 200:
            data = response.json()
            is_valid = data.get('meta', {}).get('valid', False)
            
            # Cache the result
            license_cache[license_key] = {
                'valid': is_valid,
                'data': data,
                'cached_at': datetime.now()
            }
            
            return is_valid, data
        else:
            return False, {'error': f'API returned status {response.status_code}'}
            
    except Exception as e:
        print(f'Error validating license: {str(e)}')
        return False, {'error': str(e)}

def get_license_info(license_key):
    """
    Get detailed license information from Keygen
    """
    try:
        url = f'https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT_ID}/licenses/{license_key}'
        
        headers = {
            'Authorization': f'Bearer {KEYGEN_PRODUCT_TOKEN}',
            'Accept': 'application/vnd.api+json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {'error': f'API returned status {response.status_code}'}
            
    except Exception as e:
        return False, {'error': str(e)}

def activate_license(license_key, metadata=None):
    """
    Activate a license (check-in)
    """
    try:
        url = f'https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT_ID}/licenses/{license_key}/actions/check-in'
        
        headers = {
            'Authorization': f'Bearer {KEYGEN_PRODUCT_TOKEN}',
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json'
        }
        
        payload = {}
        if metadata:
            payload['meta'] = metadata
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            return False, {'error': f'API returned status {response.status_code}'}
            
    except Exception as e:
        return False, {'error': str(e)}
