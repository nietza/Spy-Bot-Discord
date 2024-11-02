import json
import os

CONFIG_FILE = 'spy_config.json'

def load_spy_config():
    """Load spy configuration from JSON"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading spy config: {e}")
        return {}

def save_spy_config(config):
    """Save spy configuration to JSON"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving spy config: {e}")
        return False

def add_spy_target(user_id: str, channel_id: str = None, log_path: str = None):
    """Add a new spy target to configuration"""
    config = load_spy_config()
    config[user_id] = {
        'channel_id': channel_id,
        'log_path': log_path
    }
    return save_spy_config(config)

def remove_spy_target(user_id: str):
    """Remove a spy target from configuration"""
    config = load_spy_config()
    if user_id in config:
        del config[user_id]
        return save_spy_config(config)
    return False

def get_spy_targets():
    """Get all spy targets from configuration"""
    return load_spy_config()