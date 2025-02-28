import os
import json
import logging

logging.basicConfig(level=logging.INFO)

def load_deemon_config():
    config_file_path = '/root/.config/deemon/config.json'
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as config_file:
            return json.load(config_file)
    return {"deemix": {"arl": ""}, "global": {"bitrate": "128", "dark_mode": False}}

def load_deemix_config():
    config_file_path = '/root/.config/deemix/config.json'
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as config_file:
            return json.load(config_file)
    return {"arl": "", "maxBitrate": "1"}

def save_config(deemon_config, deemix_config):
    deemon_file_path = '/root/.config/deemon/config.json'
    deemix_file_path = '/root/.config/deemix/config.json'
    os.makedirs(os.path.dirname(deemon_file_path), exist_ok=True)
    os.makedirs(os.path.dirname(deemix_file_path), exist_ok=True)
    with open(deemon_file_path, 'w') as deemon_file:
        json.dump(deemon_config, deemon_file, indent=4)
    with open(deemix_file_path, 'w') as deemix_file:
        json.dump(deemix_config, deemix_file, indent=4)
    logging.info("Configurações salvas com sucesso.")