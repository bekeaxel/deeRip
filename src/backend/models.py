from datetime import date
from deemix.utils import generateReplayGainString


class Album:

    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.link = ""
        self.cover = ""
        self.cover_small = ""
        self.cover_medium = ""
        self.cover_big = ""
        self.md5 = ""
        self.release_date = ""
        self.tracklist = ""

    @classmethod
    def parse_album(cls, album_data):
        album = Album(album_data["id"], album_data["title"])

        album.link = album_data["link"]
        album.cover = album_data["cover"]
        album.cover_small = album_data["cover_small"]
        album.cover_medium = album_data["cover_medium"]
        album.cover_big = album_data["cover_big"]
        album.md5 = album_data["md5_image"]
        album.release_date = album_data["release_date"]
        album.tracklist = album_data["tracklist"]

        return album


class Artist:

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.link = ""
        self.picture = ""
        self.picture_small = ""
        self.picture_medium = ""
        self.picture_big = ""
        self.picture_xl = ""
        self.radio = False
        self.tracklist = ""

    @classmethod
    def parse_artist(cls, artist_data):
        artist = Artist(artist_data["id"], artist_data["name"])

        artist.link = artist_data["link"]
        artist.picture = artist_data["picture"]
        artist.picture_small = artist_data["picture_small"]
        artist.picture_medium = artist_data["picture_medium"]
        artist.picture_big = artist_data["picture_big"]
        artist.picture_xl = artist_data["picture_xl"]
        artist.radio = artist_data["radio"]
        artist.tracklist = artist_data["tracklist"]

        return artist


class Track:

    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.isrc = ""
        self.md5 = ""
        self.readable = False
        self.link = ""
        self.duration = 0
        self.track_position = 0
        self.disk_number = 0
        self.rank = 0
        self.release_date = ""
        self.bpm = 0
        self.gain = 0
        self.track_token = ""
        self.artist: Artist = None
        self.album: Album = None

    @classmethod
    def parse_track(cls, track_data: dict):
        track = Track(track_data["id"], track_data["title"])

        track.isrc = track_data["isrc"]
        track.md5 = track_data["md5_image"]
        track.readable = track_data["readable"]
        track.duration = track_data["duration"]
        track.track_position = track_data["track_position"]
        track.disk_number = track_data["disk_number"]
        track.rank = track_data["rank"]
        track.release_date = track_data["release_date"]
        track.bpm = track_data["bpm"]
        track.gain = generateReplayGainString(track_data["gain"])
        track.track_token = track_data["track_token"]
        track.artist = Artist.parse_artist(track_data["artist"])
        track.album = Album.parse_album(track_data["album"])

        return track
