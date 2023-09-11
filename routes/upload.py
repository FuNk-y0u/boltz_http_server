from inc        import *
from db_models  import *
from init_boltz import bolt, app

def upload():
  response = request.get_json()
  url = response['link']

  if bolt.isValidUrl(url) == True:
    itemType, itemId = bolt.parseUrl(url)
    itemName = bolt.getItemName(bolt.spClient, itemType, itemId)
    conversionToken = secrets.token_hex(8)
    downloadFolder = Path(PurePath.joinpath(Path(DOWNLOAD_FOLDER), Path(conversionToken)))
    itemSongs, totalSongs = bolt.fetchTracks(bolt.spClient, itemType, url)

    spotifyItem = item(Name = itemName, Type = itemType, itemSid = itemId, Path=downloadFolder.__str__(), Total = totalSongs, boltId=conversionToken)
    bolt_db.session.add(spotifyItem)
    bolt_db.session.commit()

    for track in itemSongs:
      spotifyTrack = song(itemId = spotifyItem.id, Name=track['name'],Artist=track['artist'],Album=track['album'],Year=track['year'], Cover=track['cover'], Genre=track['genre'],trackSid=track['spotify_id'])
      bolt_db.session.add(spotifyTrack)
    bolt_db.session.commit()

    downloadFolder.mkdir(parents=True, exist_ok=True)
    logHeader(f"saving songs to {downloadFolder}")

    conversionThread = threading.Thread(target=bolt.findAndDownload, args=(item,song,bolt_db,app, conversionToken,))
    conversionThread.start()
    
    tmpResp = {"token": conversionToken}
    return jsonify(tmpResp)
  
  else:
    return Response(status=400)

