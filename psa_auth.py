import os
import streamlit as st

def verify_license_key(key: str) -> bool:
    try:
        valid_keys = st.secrets["psa"]["valid_keys"]
        return key.strip() in valid_keys
    except Exception:
        return False

def get_user_mode(key: str) -> str:
    if verify_license_key(key):
        if key.startswith("ENT-"):
            return "enterprise"
        if key.startswith("PRO-"):
            return "pro"
        return "pro"
    return "free"
