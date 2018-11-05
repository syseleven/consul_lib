import time

from consul_lib import get_local_checks, get_failed_cluster_checks
from consul import Check


def test_get_local_checks(consul_service, consul1, consul2, consul3, consul4):
    consul_service.register(consul1, "A")
    consul_service.register(consul1, "B")
    consul_service.register(consul2, "B")
    consul_service.register(consul2, "C")
    consul_service.register(consul3, "C")
    consul_service.register(consul3, "D")

    assert set(get_local_checks(consul1)) == {"A", "B"}
    assert set(get_local_checks(consul2)) == {"B", "C"}
    assert set(get_local_checks(consul3)) == {"C", "D"}
    assert len(get_local_checks(consul4)) == 0


def test_get_local_checks_filtered(consul_service, consul1):
    consul_service.register(consul1, "A", tags=["tag1", "tag2"])
    consul_service.register(consul1, "B", tags=["tag2", "tag3"])

    assert len(get_local_checks(consul1, tags=["nonexistent"])) == 0
    assert set(get_local_checks(consul1, tags=["tag1"])) == {"A"}
    assert set(get_local_checks(consul1, tags=["tag2"])) == {"A", "B"}
    assert set(get_local_checks(consul1, tags=["tag3"])) == {"B"}


def test_get_failed_cluster_checks(consul_service, consul1, consul2, consul3, consul4):
    consul_service.register(consul1, "service1")
    consul_service.register(consul2, "service1")
    consul_service.register(consul3, "service1", check=Check.ttl("1ms"))  # failing
    consul_service.register(consul4, "service2")
    consul_service.register(consul3, "service2")
    consul_service.register(consul3, "service3")
    consul_service.register(consul2, "service4", check=Check.ttl("1ms"))  # failing

    time.sleep(0.01)

    assert set(get_failed_cluster_checks(consul1, ["service1", "service2", "service3", "service4"]).keys()) \
        == {"service:service1", "service:service4"}


def test_ignore_maintenance_fail(consul_service, consul_maint, consul1, consul2):
    consul_service.register(consul1, "service1", tags=["ignore_maintenance"])
    consul_service.register(consul2, "service1", tags=["ignore_maintenance"])
    consul_service.register(consul1, "service2")
    consul_service.register(consul2, "service2")

    consul_maint.enable(consul2, "This should not be ignored for service2")

    # TODO(sneubauer): I would expect the service name as a key here as well, so I can trace it back to service2
    assert set(get_failed_cluster_checks(consul1, ["service1", "service2"]).keys()) == {"_node_maintenance"}


def test_ignore_maintenance_success(consul_service, consul_maint, consul1, consul2):
    consul_service.register(consul1, "service1", tags=["ignore_maintenance"])
    consul_service.register(consul2, "service1", tags=["ignore_maintenance"])
    consul_service.register(consul1, "service2", tags=["ignore_maintenance"])
    consul_service.register(consul2, "service2", tags=["ignore_maintenance"])

    consul_maint.enable(consul2, "This should be ignored for service1 and service2")

    assert len(get_failed_cluster_checks(consul1, ["service1", "service2"])) == 0
