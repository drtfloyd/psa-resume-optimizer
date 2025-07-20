
import os
import streamlit as st

def verify_license_key(key: str) -> bool:
    """
    Checks if the provided license key is present in the list of valid keys
    stored in Streamlit secrets or fallback configuration.
    """
    try:
        # Try to get from Streamlit secrets first
        valid_keys = st.secrets["psa"]["valid_keys"]
        return key.strip() in valid_keys
    except KeyError:
        # Fallback to default configuration for demo purposes
        default_valid_keys = ["PSA-FREE-123", "PSA-PRO-456", "PSA-ENT-789"]
        return key.strip() in default_valid_keys
    except Exception as e:
        # Fallback to default configuration
        default_valid_keys = ["PSA-FREE-123", "PSA-PRO-456", "PSA-ENT-789"]
        return key.strip() in default_valid_keys

def get_user_mode(key: str) -> str:
    """
    Determines the user's license tier ("enterprise", "pro", "freemium", "invalid")
    based on the license key and its prefix.
    """
    # First, verify if the key is generally valid (exists in our list of known keys)
    if verify_license_key(key):
        # Now, determine the specific tier based on prefixes
        # (Assuming prefixes are consistent, e.g., "PSA-ENT-", "PSA-PRO-", "PSA-FREE-")
        normalized_key = key.strip().upper() # Normalize for consistent prefix checking

        if normalized_key.startswith("PSA-ENT-"):
            return "enterprise"
        elif normalized_key.startswith("PSA-PRO-"):
            return "pro"
        elif normalized_key.startswith("PSA-FREE-"): # Explicitly check for FREE keys
            return "freemium"
        else:
            # If valid key but prefix doesn't match known tiers, default to freemium
            # or invalid depending on your policy. For robustness, "freemium" is a safe
            # default if the key is *valid* but unrecognized prefix.
            return "freemium"
    else:
        # If verify_license_key returns False, the key is not valid or not recognized
        return "invalid"

