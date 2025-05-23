from src.backend.models import Track, SoundCloudTrack
from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TIT2,
    TPE1,
    TALB,
    TRCK,
    TLEN,
    TBPM,
    TSRC,
    APIC,
)


def tag_file(track: Track | SoundCloudTrack, path, image):
    """Tags and adds image to a file"""
    try:
        tags = ID3(path)
        tags.delete()
    except ID3NoHeaderError:
        tags = ID3()

    if isinstance(track, Track):
        # tags
        tags.add(TIT2(text=track.title))
        tags.add(TPE1(text=track.artist.name))
        tags.add(TALB(text=track.album.title))
        tags.add(TBPM(text=str(track.bpm)))
        tags.add(TSRC(text=track.isrc))
        tags.add(TRCK(text=str(track.track_position)))
        tags.add(TLEN(text=str(track.duration)))
    elif isinstance(track, SoundCloudTrack):
        tags.add(TIT2(text=track.title))
        tags.add(TPE1(text=track.artist))
        tags.add(TLEN(text=str(track.duration)))

    # image
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, data=image))

    tags.save(path, v1=2, v2_version=3, v23_sep="/")
