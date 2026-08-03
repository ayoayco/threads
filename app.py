import os
from flask import Flask
import json
from . import init_app

app = Flask(__name__)
app.config.from_file("config.json", load=json.load)
init_app(app, url_prefix='/')

## WATCH TEMPLATE FILES
template_files = os.listdir("./templates")
filtered = filter(lambda file: not file.startswith('.'), template_files)
template_files = list(filtered)
template_files = ['./templates/{0}'.format(file) for file in template_files]
extra_files = ':'.join(template_files)
print(" * Watching extra files: ")
for file in template_files:
    print(f"    - {file}")
os.environ['FLASK_RUN_EXTRA_FILES'] = extra_files

if __name__ == '__main__':
    app.run(host='0.0.0.0')
