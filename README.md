# Consul Lib [![Build Status](https://travis-ci.org/syseleven/consul_lib.svg?branch=master)](https://travis-ci.org/syseleven/consul_lib)

This library contains
- A Python implementation of [Consul Semaphore](https://www.consul.io/docs/guides/semaphore.html) and [Consul Lock](https://www.consul.io/docs/guides/leader-election.html) with session renewal in a background thread.
- A set of functions to query the cluster wide health of services in a given consul cluster. We use this, for example, in [Rebootmanager](https://github.com/syseleven/rebootmgr)

# Lock

Using [Consul Lock](https://www.consul.io/docs/guides/leader-election.html), you can make sure that only one node in your consul cluster is running a certain piece of code at the same time.

Example:

```python
import time

import consul
import consul_lib

if __name__ == '__main__':
    with consul_lib.Lock(consul.Consul(), "test/lock") as lock1:
        print("I have the lock right now! Keeping it until one minute from now.")
        time.sleep(60)

    lock1.close()
```

# Semaphore

With a [Consul Semaphore](https://www.consul.io/docs/guides/semaphore.html) you can choose how many instances of some code can run in any given moment in your consul cluster.

Example:

```python
import time

import consul
import consul_lib

if __name__ == '__main__':
    with consul_lib.Semaphore(consul.Consul(), "test/semaphore", 3) as sem1:
        print("I am one of the 3 instances of code allowed to run right now! Terminating in one minute from now.")
        time.sleep(60)

    sem1.close()
```

# LockMonitor

LockMonitor monitors a `Lock` or a `Semaphore` continously, notifying you via `threading.Event` when the lock has been lost.

This can be useful for example when implementing failover behaviour.

Example:

```python
import threading

import consul
import consul_lib
from consul_lib.session import LockMonitor

if __name__ == '__main__':
    with consul_lib.Lock(consul.Consul(), "test/lock") as lock:
        event = threading.Event()
        monitor = LockMonitor(lock, event=event)
        monitor.start()
        print("Blocking forever until the lock is lost. You can kill the lock session e.g. in the consul webinterface.")
        event.wait()
        print("Lost the lock!")
    monitor.finish()
    lock.close()
```

# Cluster service health

Example:

```python
import consul
import consul_lib

if __name__ == "__main__":
    c = consul.Consul()

    print("Checking if it is ok to do some maintenance on this node...")
    relevant_services = consul_lib.get_local_checks(c, tags=["important"])
    failed_checks = consul_lib.get_failed_cluster_checks(c, relevant_services)

    if failed_checks:
        print("You should not do maintenance right now, there are some failed checks.")
    else:
        print("It is ok to do maintenance right now.")
```

## get_local_checks

Return the names of services, that are registered on a given consul agent. You can filter services you are interested in by tags.

This is useful if you want to determine which services could be impacted if you do some kind of maintenance on that node.

## get_failed_cluster_checks

Returns a dict with all checks where the check status is != passing, provided a list of service names that you are interested in (e.g. obtained using `get_local_checks`).

# How to run the tests

You need docker-compose for the integration tests:

```shell
$ docker-compose run --rm integration_tests_py35
$ docker-compose run --rm integration_tests_py36
$ docker-compose run --rm integration_tests_py37
$ docker-compose run --rm integration_tests_py38

# For debugging purposes, you can run bash
$ docker-compose run --rm integration_tests_py37 bash

# To remove and stop everything, including images, volumes, networks etc.
docker-compose down --rmi local -v
```

You need tox for linter and safety checks:
```shell
$ tox -e lint
$ tox -e safety
```
