from db_models      import *
from init_boltz     import *

def gen():
    with app.app_context():
        bolt_db.create_all()

if __name__ == "__main__":
    gen()
