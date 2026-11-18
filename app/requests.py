"""Bounded, temporary request progress/result cache for reconnecting browsers."""
from threading import Lock
from time import monotonic

from .schemas import OCRResponse, RequestProgress


class RequestStore:
    def __init__(self, server_id: str, capacity: int = 16, ttl: float = 900):
        self.server_id, self.capacity, self.ttl = server_id, capacity, ttl
        self._records: dict[str, tuple[float, float | None, RequestProgress]] = {}
        self._lock = Lock()

    def _prune(self, now: float):
        for key, (_, finished, _) in list(self._records.items()):
            if finished is not None and now - finished >= self.ttl:
                del self._records[key]

    def prune(self):
        with self._lock:
            self._prune(monotonic())

    def begin(self, request_id: str):
        with self._lock:
            self._prune(monotonic())
            if request_id in self._records:
                raise ValueError('Request ID already exists')
            if len(self._records) >= self.capacity:
                terminal = [(finished, key) for key, (_, finished, _) in self._records.items() if finished is not None]
                if not terminal:
                    raise OverflowError('Too many active requests; try again later')
                del self._records[min(terminal)[1]]
            self._records[request_id] = (monotonic(), None, RequestProgress(
                request_id=request_id, server_id=self.server_id, phase='validating'))

    def update(self, request_id: str | None, **values):
        if request_id is None:
            return
        with self._lock:
            if request_id in self._records:
                record = self._records[request_id][2]
                for key, value in values.items():
                    setattr(record, key, value)

    def finish(self, request_id: str | None, result: OCRResponse | None = None, error: str | None = None):
        if request_id is None:
            return
        with self._lock:
            if request_id in self._records:
                began, _, record = self._records[request_id]
                record.phase = 'error' if error else 'completed'
                record.error, record.result = error, result
                self._records[request_id] = (began, monotonic(), record)

    def get(self, request_id: str) -> RequestProgress | None:
        with self._lock:
            self._prune(monotonic())
            item = self._records.get(request_id)
            if item is None:
                return None
            began, finished, record = item
            copy = record.model_copy(deep=True)
            copy.elapsed_ms = int(((finished or monotonic()) - began) * 1000)
            return copy
