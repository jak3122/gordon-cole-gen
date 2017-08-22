from gordon_cole_gen import create_app
from werkzeug.contrib.fixers import ProxyFix

app = create_app('gordon_cole_gen.settings.ProdConfig')
app.wsgi_app = ProxyFix(app.wsgi_app)

