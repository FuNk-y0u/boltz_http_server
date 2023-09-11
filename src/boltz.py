
import time
import json
import os
import sys
import spotipy
import shutil
import yt_dlp
import urllib.request
import mutagen

from pathlib import Path, PurePath
from spotipy.oauth2 import SpotifyClientCredentials

from src.config import CLIENT_ID, CLIENT_SECRET, DOWNLOAD_FOLDER, ZIP_LOCATION
from src.boltz_util import *

from os import path
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3

class boltz:
    # ** create spotify client
    def __init__(self, CLIENT_ID = CLIENT_ID, CLIENT_SECRET = CLIENT_SECRET):
        self.spClient = self.createSp(CLIENT_ID, CLIENT_SECRET)
    
    # ** zips files
    def zipFiles(self, token):
        shutil.make_archive(f'{ZIP_LOCATION}/{token}',format='zip', root_dir=f'{DOWNLOAD_FOLDER}{token}/')

    # ** sets music cover 
    def setTags(self,song,spotifyItem, filename, index):
        try:
            song_file = MP3(filename, ID3=EasyID3)
        except mutagen.MutagenError as e:
            logError(e)
            logError(
                f"Failed to fetch tags, skipping"
            )
            return
        song_file["date"] = song.Year
        song_file["tracknumber"] = (str(index) + "/" + str(spotifyItem.Total))
        song_file["genre"] = song.Genre
        song_file.save()


        song_file = MP3(filename, ID3=ID3)
        cover = song.Cover
        if cover is not None:
            if cover.lower().startswith("http"):
                req = urllib.request.Request(cover)
            else:
                raise ValueError from None
            with urllib.request.urlopen(req) as resp:  # nosec
                song_file.tags["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=resp.read(),
                )
        song_file.save()

    # ** Finds and Downloads 
    def findAndDownload(self, item, song, db,app, conversionToken):
        with app.app_context():
            index = 1
            spotifyItem = item.query.filter_by(boltId=conversionToken).first()
            spotifySong = song.query.filter_by(itemId=spotifyItem.id).all()
            for song in spotifySong:
                
                name = song.Name
                artist = song.Artist
                album = song.Album
                

                query = f"{artist} - {name} Lyrics".replace(":","").replace('"',"")
                fileName = f"{artist} - {name}", index
                filePath = path.join(spotifyItem.Path, fileName[0])
                mp3FileName = f"{filePath}.mp3"
                mp3FilePath = path.join(mp3FileName)

                sponsorblockPostprocessor = [
                        {
                            "key": "SponsorBlock",
                            "categories": ["skip_non_music_sections"],
                        },
                        {
                            "key": "ModifyChapters",
                            "remove_sponsor_segments": ["music_offtopic"],
                            "force_keyframes": True,
                        },
                ]
                outtmpl = f"{filePath}.%(ext)s"
                ydlOpts = {
                    "quiet":True,
                    "proxy": "",
                    "default_search": "ytsearch",
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "postprocessors": sponsorblockPostprocessor,
                    "noplaylist": True,
                    "no_color": False,
                    "postprocessor_args": [
                        "-metadata",
                        "title=" + name,
                        "-metadata",
                        "artist=" + artist,
                        "-metadata",
                        "album=" + album,
                    ],
                }
                mp3PostprocessOpts = {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
                ydlOpts["postprocessors"].append(mp3PostprocessOpts.copy())


                with yt_dlp.YoutubeDL(ydlOpts) as ydl:
                    song.Status = "DOWNLOADING"
                    db.session.commit()

                    try:
                        ydl.download([query])
                        
                    except Exception as e:
                        song.Status = "ERROR"
                        db.session.commit()
                        logError(e)
                        logError(f"Failed to download {name}, make sure yt_dlp is up to date")
                song.Status = "CONVERTING"
                db.session.commit()
                self.setTags(song,spotifyItem, mp3FileName, index)
                song.Status = "DONE"
                db.session.commit()
                spotifyItem.Progress = str(round((index/int(spotifyItem.Total)*100)))
                db.session.commit()
                index += 1
            self.zipFiles(spotifyItem.boltId)
            spotifyItem.isCompleted = True
            db.session.commit()

    # ** gets song meta data
    def fetchTracks(self,sp,item_type,url):
        songs_list = []
        offset = 0
        songs_fetched = 0
        total_songs = 0

        if item_type == "playlist":
            while True:
                
                items = sp.playlist_items(
                    playlist_id=url,
                    fields="items.track.name,items.track.artists(name, uri),"
                    "items.track.album(name, release_date, total_tracks, images),"
                    "items.track.track_number,total, next,offset,"
                    "items.track.id",
                    additional_types=["track"],
                    offset=offset,
                )
                total_songs = items.get("total")
                for item in items["items"]:
                    track_info = item.get("track")
                    if track_info is None:
                        offset += 1
                        continue
                    track_album_info = track_info.get("album")
                    track_num = track_info.get("track_number")
                    spotify_id = track_info.get("id")
                    track_name = track_info.get("name")
                    track_artist = ",".join(
                        [artist["name"] for artist in track_info.get("artists")]
                    )
                    if track_album_info:
                        track_album = track_album_info.get("name")
                        track_year = (
                            track_album_info.get("release_date")[:4]
                            if track_album_info.get("release_date")
                            else ""
                        )
                        album_total = track_album_info.get("total_tracks")
                    if len(item["track"]["album"]["images"]) > 0:
                        cover = item["track"]["album"]["images"][0]["url"]
                    else:
                        cover = None
                    artists = track_info.get("artists")
                    main_artist_id = (
                        artists[0].get("uri", None) if len(artists) > 0 else None
                    )
                    genres = (
                        sp.artist(artist_id=main_artist_id).get("genres", [])
                        if main_artist_id
                        else []
                    )
                    if len(genres) > 0:
                        genre = genres[0]
                    else:
                        genre = ""
                    songs_list.append(
                        {
                            "name": track_name,
                            "artist": track_artist,
                            "album": track_album,
                            "year": track_year,
                            "num_tracks": album_total,
                            "num": track_num,
                            "playlist_num": offset + 1,
                            "cover": cover,
                            "genre": genre,
                            "spotify_id": spotify_id,
                            "track_url": None,
                        }
                    )
                    offset += 1
                    songs_fetched += 1

                if total_songs == offset:
                    break

        elif item_type == "album":
            while True:
                album_info = sp.album(album_id=url)
                items = sp.album_tracks(album_id=url, offset=offset)
                total_songs = items.get("total")
                track_album = album_info.get("name")
                track_year = (
                    album_info.get("release_date")[:4]
                    if album_info.get("release_date")
                    else ""
                )
                album_total = album_info.get("total_tracks")
                
                if len(album_info["images"]) > 0:
                    cover = album_info["images"][0]["url"]
                else:
                    cover = None
                if (
                    len(sp.artist(artist_id=album_info["artists"][0]["uri"])["genres"])
                    > 0
                ):
                    genre = sp.artist(artist_id=album_info["artists"][0]["uri"])[
                        "genres"
                    ][0]
                else:
                    genre = ""
                for item in items["items"]:
                    track_name = item.get("name")
                    track_artist = ", ".join(
                        [artist["name"] for artist in item["artists"]]
                    )
                    track_num = item["track_number"]
                    spotify_id = item.get("id")
                    songs_list.append(
                        {
                            "name": track_name,
                            "artist": track_artist,
                            "album": track_album,
                            "year": track_year,
                            "num_tracks": album_total,
                            "num": track_num,
                            "track_url": None,
                            "playlist_num": offset + 1,
                            "cover": cover,
                            "genre": genre,
                            "spotify_id": spotify_id,
                        }
                    )
                    offset += 1
                if album_total == offset:
                    break
        elif item_type == "track":
            items = sp.track(track_id=url)
            track_name = items.get("name")
            album_info = items.get("album")
            track_artist = ", ".join([artist["name"] for artist in items["artists"]])
            if album_info:
                track_album = album_info.get("name")
                track_year = (
                    album_info.get("release_date")[:4]
                    if album_info.get("release_date")
                    else ""
                )
                album_total = album_info.get("total_tracks")
            track_num = items["track_number"]
            spotify_id = items["id"]

            if len(items["album"]["images"]) > 0:
                cover = items["album"]["images"][0]["url"]
            else:
                cover = None
            if len(sp.artist(artist_id=items["artists"][0]["uri"])["genres"]) > 0:
                genre = sp.artist(artist_id=items["artists"][0]["uri"])["genres"][0]
            else:
                genre = ""
            songs_list.append(
                {
                    "name": track_name,
                    "artist": track_artist,
                    "album": track_album,
                    "year": track_year,
                    "num_tracks": album_total,
                    "num": track_num,
                    "playlist_num": offset + 1,
                    "cover": cover,
                    "genre": genre,
                    "track_url": None,
                    "spotify_id": spotify_id,
                }
            )

        return songs_list, total_songs

    def getItemName(self,spClient,itemType,itemId):
        if itemType == "playlist":
            name = spClient.playlist(playlist_id=itemId, fields="name").get("name")
        elif itemType == "album":
            name = sp.album(album_id=itemId).get("name")
        elif itemType == "track":
            name = sp.track(track_id=itemId).get("name")
        return self.sanitize(name)
    
    def sanitize(self,name,replace_with = ""):
        clean_up_list = ["\\", "/", ":", "*", "?", '"', "<", ">", "|", "\0", "$", "\""]
        for x in clean_up_list:
            name = name.replace(x, replace_with)
        return name
    
    def createSp(self,clientId, clientSecret):
        try:
            __spotifyClient = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
            )
            logHeader("Sucessfully created spotify client")
            return __spotifyClient

        except Exception as e:
            logError("Unable To Create Spotify Client")
            logError(e)

    def parseUrl(self,url):
        if url.startswith("https://open.spotify.com/"):
            parsedUrl = url.replace("https://open.spotify.com/", "").split("?")[0]
            itemType = parsedUrl.split("/")[0]
            itemId = parsedUrl.split("/")[1]
            return itemType, itemId
        else:
            logError("Invalid Url")
            return "ERROR", "ERROR"

    def isValidUrl(self,url):
        itemType, itemId = self.parseUrl(url)
        if itemType not in ["album", "track", "playlist"]:
            logError(f"Only albums/tracks/playlists are supported and not {itemType}")
            return False
        if itemId is None:
            logError(f"Couln't get valid item id for {url}")
            return False
        else:
            return True

