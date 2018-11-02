from consul_lib import Semaphore


def test_semaphore_success(consul1, consul2):
    entered = 0
    with Semaphore(consul1, "test/semaphore", 2) as sem1:
        entered += 1
        assert sem1.acquired()
        with Semaphore(consul2, "test/semaphore", 2) as sem2:
            entered += 1
            assert sem2.acquired()
    assert entered == 2
    # TODO(sneubauer): Acquired should be a property, analogous to the Lock's acquired
    assert not sem1.acquired()
    assert not sem2.acquired()
    # TODO(sneubauer): If you don't close the sem, the process never terminates. This can't be right.
    sem1.close()
    sem2.close()


def test_semaphore_failing(consul1, consul2):
    entered = False
    with Semaphore(consul1, "test/semaphore", 1) as sem1:
        entered = True
        assert sem1.acquired()
        sem2 = Semaphore(consul2, "test/semaphore", 1)
        assert not sem2.acquire(blocking=False)
        assert not sem2.acquired()
    assert entered
    assert not sem1.acquired()
    assert not sem2.acquired()
    sem1.close()
    sem2.close()
