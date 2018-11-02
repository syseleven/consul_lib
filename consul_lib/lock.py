import atexit
import logging
from pathlib import Path
from .session import SessionRenewer

LOG = logging.getLogger(__name__)


class Lock:

    def __init__(self, con, prefix, *, session=None, payload='{"state": "done"}'):
        """
        Context manager to use consul session to create a mutex.
        Have a look at: https://www.consul.io/docs/guides/leader-election.html

        Creates a prefix/.lock to synchronize.

        :param con: python-consul consul.Consul.
        :param prefix: prefix to use to. E.g. services/my-service.
        :param session: create a new Lock object, but reuse session.
        :param payload: content of the lock during time of lock. Could be anything human readable.
        """
        self._con = con
        self._prefix = Path(prefix)
        self._path = self._prefix / ".lock"
        self._payload = payload
        self._ttl = 60
        if session:
            self.session = session
        else:
            self.session = None
        self.session_renewer = None
        self.locked = False

    @property
    def acquired(self):
        _, consul_data = self._con.kv.get(str(self._path))
        return consul_data and "Session" in consul_data and consul_data["Session"] == self.session

    def reset_session(self):
        self.session = None

    def acquire(self, *, blocking=True, wait=None):
        """
        :param blocking: Wait for someone else or release the Lock. Default True.
                         In long running programs this is the best solution.
                         Using consul from a web application should not block, but warn.
                         Take care to .close() when you are done.
        :param wait: Maximum duration to wait for a key change (e.g. 10s)
        """
        # Create a session with a ttl of 60s.
        # So it is possible to find broken clients.
        if not self.session:
            LOG.debug("Starting session.")
            self.session = self._con.session.create(ttl=self._ttl)
            # Kick off a Thread to periodically renew the session
            # Reason:
            # During acquire, a prefix/session is acquire=session.
            # If a Holder fails, without cleanup, it would stuck in Holders.
            # With a session with, ttl and renew of this session, broken
            # clients can be detected and removed from Holders.
            if self.session_renewer and self.session_renewer.is_alive():
                self.session_renewer._session = self.session
            else:
                LOG.debug("Starting session_renewer.")
                self.session_renewer = SessionRenewer(self.session, self._con)
                self.session_renewer.start()
        while not self._con.kv.put(str(self._path), self._payload, acquire=self.session):
            # getting the current index …
            idx, _ = self._con.kv.get(str(self._path))

            # … and watching for updates
            # infact, this blocks the program until the data changes
            # within consul.
            if blocking:
                LOG.debug("Waiting for lock on %s.", self._path)
                _, data = self._con.kv.get(str(self._path), index=idx, wait=wait)
                if wait and data and int(data["ModifyIndex"]) == int(idx):
                    LOG.debug("No state change within %s", wait)
                    return False
            else:
                LOG.debug("Could not aquire lock on %s.", self._path)
                return False
        self.locked = True
        return True

    def release(self, *, keep_session=None, blocking=True):
        """
        With keep_session set to always, it is possible, to store the session
        somewhere release it later.

        :param keep_session: Release the Lock, but still keep the session.
                             Default None. always: just keep. exit: until end
                             of program.
        """
        LOG.debug("Releasing lock %s.", self._path)
        self._con.kv.put(str(self._path), None, release=self.session)
        if keep_session == "always":
            pass
        elif keep_session == "exit":
            # register this session to be cleaned up
            atexit.register(lambda x: x.close(), self)
        else:
            self.close(blocking=blocking)
        self.locked = False

    def close(self, blocking=True, timeout=None):
        if self.session:
            LOG.debug("Closing session %s.", self.session)
            try:
                self._con.session.destroy(self.session)
            except Exception:
                LOG.debug("Unable to destroy session. Consul not available.")
            self.session = None
        self.locked = False
        if self.session_renewer:
            self.session_renewer.finish()
            if blocking:
                LOG.debug("Waiting for SessionRenewer-Thread to terminate.")
                self.session_renewer.join(timeout)

    def __enter__(self):
        if self.acquire():
            return self
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
