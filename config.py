import json

def read_config():
    with open('config.json', mode='r', encoding='utf-8') as file:
        config = json.load(file)
        print("Config keys:", config.keys())  # Debug print
        return config

def write_config(config):
    try:
        with open('config.json', mode='w', encoding='utf-8') as file:
            json.dump(config, file, indent=4)
            print("Config updated successfully")
    except Exception as e:
        print(f"Error writing to config.json: {e}")
