from flask import current_app

### config accessors shared by the blueprints
def server():
    return current_app.config['APPS']['threads']['server']

def get_attribution():
    return current_app.config['ATTRIBUTION']

def get_app_config():
    return current_app.config['APPS']['threads']

def get_user_id():
    return str(current_app.config['APPS']['threads']['user_id'])
