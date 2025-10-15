from datetime import datetime, timedelta

class Cache:
    def __init__(self, expire_minutes=30):
        self.cache = {}
        self.expire_minutes = expire_minutes

    def get(self, key):
        if key in self.cache:
            item = self.cache[key]
            if datetime.now() < item['expires']:
                return item['data']
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = {
            'data': value,
            'expires': datetime.now() + timedelta(minutes=self.expire_minutes)
        }
