class InvalidSpotifyLinkException(Exception):
    def __init__(self, message="Invalid Spotify link"):
        self.message = message
        super().__init__(self.message)


class ISRCNotAvailableOnSpotifyException(Exception):
    def __init__(self, message="Isrc was not found in track metadata"):
        self.message = message
        super().__init__(self.message)


class DowloadEmptyException(Exception):
    def __init__(self, message="Download is empty"):
        self.message = message
        super().__init__(message)


class TrackNotFoundOnDeezerException(Exception):
    def __init__(
        self, message="The track could not be found on deezer. Try manual search."
    ):
        self.message = message
        super().__init__(self.message)


class ConversionError:
    def __init__(self, id, title, artist, album):
        self.id = id
        self.title = title
        self.artist = artist
        self.album = album

    def __str__(self):
        return f"title={self.title},\nartist={self.artist},\nalbum={self.album}"


class ConversionCancelledException(Exception):
    def __init__(self, message="Conversion cancelled"):
        self.message = message
        super().__init__(self.message)


class DownloadException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class SoundCloudError(Exception):
    def __init__(self, message="Soundcloud error"):
        self.message = message
        super().__init__(self.message)
