import threading

import pytest

from consul_lib import Lock, Semaphore
from consul_lib.session import LockMonitor


@pytest.mark.parametrize("get_lock", [
    lambda con: Lock(con, "test/lock"),
    lambda con: Semaphore(con, "test/semaphore", 1),
])
def test_lockmonitor(consul1, get_lock):
    lock = get_lock(consul1)

    assert lock.acquire(), "Could not acquire lock"

    event = threading.Event()
    mon = LockMonitor(lock, event=event)
    mon.start()
    assert not event.is_set()

    # Destroy session and wait for event to be set
    consul1.session.destroy(lock.session)
    assert event.wait(timeout=30), "Event has not been set"

    lock.release()
    lock.close()
    mon.finish()
