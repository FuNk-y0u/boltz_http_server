from inc        import *
from db_models  import *
from init_boltz import app

from routes.upload  import upload
from routes.status  import status, stats
from routes.download  import download

# routes
app.add_url_rule("/", view_func=upload, methods=["POST"])
app.add_url_rule("/<token>", view_func=status, methods=["GET"])
app.add_url_rule("/download/<token>", view_func=download, methods=["GET"])

if __name__ == '__main__':
  app.run(host=SERVER_IP, port=PORT, debug=True)
