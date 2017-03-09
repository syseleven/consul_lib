import logging
import threading
import time

LOG = logging.getLogger(__name__)


class SessionRenewer(threading.Thread):

    def __init__(self, session, con, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = session
        self._con = con
        self._finished = False

    def run(self):
        """ Renew the session in a 5 second interval """
        while not self._finished:
            try:
                self._con.session.renew(self._session)
            except:
                LOG.warn("Unable to renew session.")
                # We do not want to return on failure, since a leader election
                # in the consul cluster can cause a failure of renew.
                # It is accepted, that this code runs until the finished-flag
                # is set.
            time.sleep(5)

    def finish(self):
        self._finished = True


class LockMonitor(threading.Thread):

    def __init__(self, lock, retries=2, retry_time=2, event=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._finished = False
        self._lock = lock
        self._lost = False
        self._retries = retries
        self._event = event
        self._retry_time = retry_time

    def run(self):
        retries = 0
        while not self._finished and not self._lost:
            if self._lock.session:
                if retries > self._retries:
                    self._lost = True
                else:
                    try:
                        if self._lock.locked:
                            _, data = self._lock._con.kv.get(str(self._lock._path))
                            if not data:
                                self._lost = True
                            elif data and data.get("Session", "") != self._lock.session:
                                self._lost = True
                            else:
                                retries = 0
                        else:
                            self._lost = False
                    except:
                        LOG.warn("Unable to get lock. Trying again.", exc_info=True)
                        retries += 1
            if self._lost and self._event:
                # Firing the event if there is one.
                LOG.debug("LockMonitor firing event")
                self._event.set()
            time.sleep(self._retry_time)

    def reset(self):
        self._lost = False
        self._retries = 0

    def finish(self):
        self._finished = True
