import json
import os

MIRROR_CONFIG_FILE = 'MirrorCFG.json'

def load_mirror_config():
    try:
        if os.path.exists(MIRROR_CONFIG_FILE):
            with open(MIRROR_CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading mirror config: {e}")
        return {}
def save_mirror_config(config):
    try:
        with open(MIRROR_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving mirror config: {e}")
        return False
def add_mirror_channel(source_id: str, target_id: str):
    config = load_mirror_config()
    config[source_id] = target_id
    return save_mirror_config(config)
def remove_mirror_channel(source_id: str):
    config = load_mirror_config()
    if source_id in config:
        del config[source_id]
        return save_mirror_config(config)
    return False
def get_mirror_channels():
    return load_mirror_config()