from inc        import *
from db_models  import *


app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///items.db'
bolt_db.init_app(app)
bolt = boltz()