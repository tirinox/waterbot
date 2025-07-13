import json
from datetime import datetime


class DB:
    def __init__(self, filename='db.json', save_every: int = 10):
        self.filename = filename
        self._data = {}
        self.save_every = save_every
        self._save_counter = 0

    def load(self):
        try:
            with open(self.filename, 'r') as f:
                self._data = json.load(f)
        except FileNotFoundError:
            self._data = {}

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self._data, f)

    def save_sometimes(self):
        self._save_counter += 1
        print(self._save_counter)

        if self._save_counter >= self.save_every:
            self.save()
            self._save_counter = 0

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)


class Cooldown:
    def __init__(self, db: DB, key: str, period_sec: float):
        self.db = db
        self._key = key
        self.period_sec = period_sec

    @property
    def key(self):
        return f'{self._key}:cooldown'

    def read_last_trigger_ts(self):
        return self.db.get(self.key, 0)

    def do(self):
        if self.can_do():
            self.db[self.key] = datetime.now().timestamp()
            self.db.save_sometimes()

    def can_do(self):
        return datetime.now().timestamp() > self.read_last_trigger_ts() + self.period_sec
