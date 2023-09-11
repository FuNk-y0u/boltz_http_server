from inc        import *
from db_models  import *
from init_boltz import bolt

def download(token):
  if os.path.exists(f'{ZIP_LOCATION}{token}.zip'):
    return send_file(f'{ZIP_LOCATION}{token}.zip')
  else:
    return Response(status=404)