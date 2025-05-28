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


class ConversionCancelledException(Exception):
    def __init__(self, message="Conversion cancelled"):
        self.message = message
        super().__init__(self.message)


class DownloadException(Exception):
    def __init__(self, message="Download failed"):
        self.message = message
        super().__init__(self.message)


class SoundCloudError(Exception):
    def __init__(self, message="Soundcloud error"):
        self.message = message
        super().__init__(self.message)
