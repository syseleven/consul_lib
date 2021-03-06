from consul_lib import Lock


def test_lock_success(consul1, consul2):
    with Lock(consul1, "test/lock") as lock1:
        assert lock1.acquired

    assert not lock1.acquired

    # TODO(sneubauer): If you don't close the lock, the process never terminates. This can't be right.
    lock1.close()


def test_lock_failing(consul1, consul2):
    lock1 = Lock(consul1, "test/lock")
    assert not lock1.acquired

    with lock1:
        lock2 = Lock(consul2, "test/lock")
        assert not lock2.acquire(wait="100ms"), "lock2 and lock1 are held at the same time"
        assert not lock2.acquired
        assert lock1.acquired

    lock1.close()
    lock2.close()
