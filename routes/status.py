from inc        import *
from db_models  import *
from init_boltz import bolt

def status(token):
  spotifyItem = item.query.filter_by(boltId=token).first()

  if(spotifyItem == None):
    return Response(status=404)
  
  spotifySongs = song.query.filter_by(itemId = spotifyItem.id).all()
  
  response = {
    "Name":spotifyItem.Name,
    "Type":spotifyItem.Type,
    "Progress": spotifyItem.Progress,
    "boltId": spotifyItem.boltId,
    "isCompleted": spotifyItem.isCompleted,
    "songs": [],
  }
  for track in spotifySongs:
    song_detail = {
      "Name": track.Name,
      "Artist": track.Artist,
      "Album": track.Album,
      "Year": track.Year,
      "Genre": track.Genre,
      "Status": track.Status,
      "Cover": track.Cover
    }
    response["songs"].append(song_detail)
  
  return jsonify(response)