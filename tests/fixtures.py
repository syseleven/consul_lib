import pytest
import consul


@pytest.fixture
def consul1():
    return _wait_for_leader(consul.Consul(host="consul1"))


@pytest.fixture
def consul2():
    return _wait_for_leader(consul.Consul(host="consul2"))


@pytest.fixture
def consul3():
    return _wait_for_leader(consul.Consul(host="consul3"))


@pytest.fixture
def consul4():
    return _wait_for_leader(consul.Consul(host="consul4"))


@pytest.fixture
def consul_maint():
    f = _ConsulMaintFixture()
    yield f
    f.restore()


@pytest.fixture
def consul_service():
    f = _ConsulServiceFixture()
    yield f
    f.restore()


def _wait_for_leader(c):
    import time
    while not c.status.leader():
        time.sleep(.1)
    return c


class _ConsulServiceFixture:
    def __init__(self):
        self.registered_services = []

    def register(self, consul_client, name, *args, service_id=None, **kwargs):
        consul_client.agent.service.register(name, *args, **kwargs)
        self.registered_services += [(consul_client, service_id or name)]

    def restore(self):
        for consul_client, service_name in self.registered_services:
            consul_client.agent.service.deregister(service_name)


class _ConsulMaintFixture:
    def __init__(self):
        self._enabled = []

    def enable(self, consul_client, reason=None):
        consul_client.agent.maintenance(True, reason)
        self._enabled += [consul_client]

    def disable(self, consul_client):
        consul_client.agent.maintenance(False)

    def restore(self):
        for client in self._enabled:
            self.disable(client)
