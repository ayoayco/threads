import os
from flask import Flask
import json
from .threads import threads
from .cache import cache

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache'})
app.register_blueprint(threads, url_prefix='/')
app.config.from_file("config.json", load=json.load)

## WATCH TEMPLATE FILES
template_files = os.listdir("./templates")
filtered = filter(lambda file: not file.startswith('.'), template_files)
template_files = list(filtered)
template_files = ['./templates/{0}'.format(file) for file in template_files]
extra_files = ':'.join(template_files)
print(" * Watching: ")
for file in template_files:
    print(f"    - {file}")
os.environ['FLASK_RUN_EXTRA_FILES'] = extra_files

if __name__ == '__main__':
    app.run(host='0.0.0.0')
