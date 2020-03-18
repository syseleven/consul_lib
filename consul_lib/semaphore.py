import atexit
import json
import logging
import socket
from pathlib import Path
from .session import SessionRenewer

LOG = logging.getLogger(__name__)


class Semaphore:

    def __init__(self, con, prefix, size, *, session=None):
        """
        Context manager to use consul session to create a semaphore.
        Have a look at: https://www.consul.io/docs/guides/semaphore.html

        Creates a prefix/.lock to synchronize. Beside this, it uses the session
        to create intermediate locks with prefix/session. The contents of payload
        will be written to this lock, and _not_ to prefix/.lock!

        :param con: python-consul consul.Consul.
        :param prefix: prefix to use to. E.g. services/my-service.
        :param payload: content of the lock during time of lock. Could be anything human readable. Default: lock
        """
        if session:
            self.session = session
        else:
            # Create a session with a ttl of 60s.
            # So it is possible to find broken clients.
            self.session = con.session.create(ttl=60)
        # Kick off a Thread to periodically renew the session
        # Reason:
        # During acquire, a prefix/session is acquire=session.
        # If a Holder fails, without cleanup, it would stuck in Holders.
        # With a session with, ttl and renew of this session, broken
        # clients can be detected and removed from Holders.
        self.session_renewer = SessionRenewer(self.session, con)
        self.session_renewer.start()
        self._con = con
        self.prefix = Path(prefix)
        self.size = size
        self.lock_path = str(self.prefix / ".lock")

    def _cleanup_holders(self, holders):
        _, contender = self._con.kv.get(str(self.prefix), recurse=True)
        if contender:
            LOG.debug("Cleaning up broken clients.")
            abandoned = [x for x in contender if not x["Key"].endswith(".lock") and "Session" not in x]
            abandoned_sessions = [x["Key"].split("/")[-1] for x in abandoned]
            for broken in abandoned:
                self._con.kv.delete(broken["Key"])
            LOG.debug("Holders before: %s", holders)
            holders = [x for x in holders if x not in abandoned_sessions]
            LOG.debug("Holders after: %s", holders)
        return holders

    def acquire(self, *, blocking=True):
        """
        Returns True, or False if the Semaphore could not be acquired.

        :param blocking: Wait for someone else or release the Lock. Default True.
                         In long running programs this is the best solution.
                         Using consul from a web application should not block, but warn.
                         Take care to .close() when you are done.
        """
        # This value (socket.gethostname) does not have any technical matter.
        res = self._con.kv.put(str(self.prefix / self.session), socket.gethostname(), acquire=self.session)
        if not res:
            return False

        acquired = False
        idx = None
        while not acquired:
            LOG.debug("Trying to obtain lock")
            # If not blocking, we do not care about the index and just need a result.
            # It is up to the caller to act appropriate.
            if not blocking:
                idx = None
            # Using a wait at this get.
            # Imagine there is a Semaphore(2), and 2 processes are running and 1 is waiting.
            # Both active clients crash. So no update on consul will happen and this get
            # waits until a timeout, to rerun the loop. The timeout by default is 5 minutes.
            # However. This code loops until the lock can be obtained (as long as blocking=True).
            idx, data = self._con.kv.get(self.lock_path, index=idx or None, wait="30s")
            if data:
                value = json.loads(data["Value"].decode())
            else:
                value = {"Limit": self.size,
                         "Holders": []}
                # put of data only if lock_path does not exist on put.
                idx = 0
            # Force setting the Limit parameter.
            # Needed because the Semaphore may exist in consul, but the parameter
            # In the calling code may change. All User of this Semaphore must have
            # the same opinion about self.size!
            value["Limit"] = self.size

            # Cleanup. Remove broken clients from Holders.
            value["Holders"] = self._cleanup_holders(value["Holders"])

            if self.session in value["Holders"]:
                return True
            if len(value["Holders"]) < value["Limit"]:
                value["Holders"].append(self.session)
                res = self._con.kv.put(self.lock_path, json.dumps(value), cas=idx)
                if res:
                    acquired = True
            if not blocking:
                # Return out of the while loop without retrying to acquire lock
                break
        return acquired

    def acquired(self):
        if not self.session:
            return False
        idx, data = self._con.kv.get(self.lock_path)
        if not data:
            return False
        value = json.loads(data["Value"].decode())
        # Be a bit more careful and check if Holders exists in value.
        # A KeyError at this point would prevent a cleanup.
        return "Holders" in value and self.session in value["Holders"]

    def release(self, *, keep_session=None, blocking=True):
        released = False
        idx = None
        while not released:
            LOG.debug("Waiting to release lock")
            idx, data = self._con.kv.get(self.lock_path, index=idx)
            if not data:
                LOG.debug("No lock found, so it is not used by us.")
                return True
            value = json.loads(data["Value"].decode())

            if self.session not in value["Holders"]:
                LOG.debug("We do not hold this lock.")
                return True

            value["Holders"].remove(self.session)
            # Optimistic put. May need to be retried.
            res = self._con.kv.put(self.lock_path, json.dumps(value), cas=idx)
            if res:
                released = True
            if not blocking:
                # Return out of the while loop without retrying to release lock
                break
        if keep_session == "exit":
            # register this session to be cleaned up
            atexit.register(lambda x: x.close(blocking), self)
        else:
            self.close(blocking)
        return released

    def close(self, blocking=True):
        if self.session:
            LOG.debug("Closing session %s.", self.session)
            self._con.kv.delete(str(self.prefix / self.session))
            self._con.session.destroy(self.session)
            self.session = None
        self.session_renewer.finish()
        if blocking:
            LOG.debug("Waiting for SessionRenewer-Thread to terminate.")
            self.session_renewer.join()

    def __enter__(self):
        if self.acquire():
            return self
        return None

    def __exit__(self, exc_type, exec_val, exec_tb):
        self.release()
        return False
