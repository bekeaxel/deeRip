from deezer import Deezer
from src.backend.deezer_utils import DeezerUtils


if __name__ == "__main__":

    dz = Deezer()
    dz.login_via_arl(
        "c22dd6141a9c3cd0d1b9d4e3a4219355ab24a74ff2c1962d6912948851946eb91ec4e09b8cdc0437c8dd525cbe0ee24bd7129639eec5480abd092860ca508c15afd0f96980f52d2d83c67784086c294721bd19cab3e98284f389d524d38cf5e8"
    )

    utils = DeezerUtils(dz)

    utils.search("dark side of the moon")
