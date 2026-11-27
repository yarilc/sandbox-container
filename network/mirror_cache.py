"""Bounded per-session cache for complete dependency objects."""

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
import time


@dataclass
class Entry:
    path: Path
    response: tuple
    size: int
    expires: float
    readers: int = 0


class Cache:
    def __init__(self, directory, *, capacity=128 << 20, object_limit=32 << 20, entries=256, ttl=300):
        self.directory = Path(directory)
        self.capacity = capacity
        self.object_limit = object_limit
        self.entry_limit = entries
        self.ttl = ttl
        self.entries = OrderedDict()
        self.pending = set()
        self.used = 0

    def remove(self, key):
        entry = self.entries.pop(key)
        entry.path.unlink(missing_ok=True)
        self.used -= entry.size

    @contextmanager
    def read(self, key):
        entry = self.entries.get(key)
        if entry is None or entry.expires <= time.monotonic():
            if entry is not None and not entry.readers:
                self.remove(key)
            yield None
            return
        self.entries.move_to_end(key)
        entry.readers += 1
        try:
            with entry.path.open('rb') as handle:
                yield entry.response, handle
        finally:
            entry.readers -= 1

    def reserve(self, key, size):
        if key in self.entries or key in self.pending or size > min(self.object_limit, self.capacity):
            return False
        while self.used + size > self.capacity or len(self.entries) + len(self.pending) >= self.entry_limit:
            for older, entry in self.entries.items():
                if not entry.readers:
                    self.remove(older)
                    break
            else:
                return False
        self.pending.add(key)
        self.used += size
        return True

    @contextmanager
    def write(self, key, response):
        size = response[2]
        if size is None or not self.reserve(key, size):
            yield None
            return
        path = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.directory, prefix='.partial-', delete=False) as handle:
                path = Path(handle.name)
                yield handle
                if handle.tell() != size:
                    return
            final = path.with_name(path.name.replace('.partial-', 'object-', 1))
            os.replace(path, final)
            self.entries[key] = Entry(final, response, size, time.monotonic() + self.ttl)
        finally:
            self.pending.remove(key)
            if key not in self.entries:
                self.used -= size
            if path is not None:
                path.unlink(missing_ok=True)
