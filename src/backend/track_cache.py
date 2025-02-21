import diskcache


class Cache:

    def __init__(self, cache_path="../../cache"):
        self.cache = diskcache.Cache(cache_path)

    def get(self, id):
        if id in self.cache:
            # print(f"Cache hit for {id}")
            return self.cache[id]
        return None

    def store(self, spotify_id, deezer_data):
        self.cache.set(spotify_id, deezer_data)

    def close(self):
        self.cache.close()
