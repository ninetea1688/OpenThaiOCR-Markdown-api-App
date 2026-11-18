"""Loading failures must wake HTTP requests waiting for the model."""
import threading

from app.config import Settings
from app.engine import OCREngine


def test_failed_background_load_releases_waiters(monkeypatch):
    engine = OCREngine(Settings(_env_file=None, preload=False))
    entered, fail, waiting = threading.Event(), threading.Event(), threading.Event()
    errors = []
    original_wait = engine._ready.wait

    def load():
        entered.set()
        assert fail.wait(2)
        raise ValueError('invalid model')

    def wait(timeout=None):
        waiting.set()
        return original_wait(timeout)

    def request():
        try:
            engine.wait_ready(timeout=2)
        except Exception as exc:
            errors.append(exc)

    monkeypatch.setattr(engine, '_load', load)
    monkeypatch.setattr(engine._ready, 'wait', wait)
    engine.start_background_load()
    assert entered.wait(2)
    waiter = threading.Thread(target=request, daemon=True)
    waiter.start()
    assert waiting.wait(2)
    fail.set()
    waiter.join(2)
    assert not waiter.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert 'invalid model' in str(errors[0])
