import logging

LOG = logging.getLogger(__name__)


def get_local_checks(con, tags=[]):
    """
    Returns a list with all checks for this agent (local checks).
    If tags is provided only checks are returned which have at least on tag in common.
    """

    if tags:
        checks = [k for k, v in con.agent.services().items() if v["Tags"] and set(tags).intersection(set(v["Tags"]))]
    else:
        checks = con.agent.services().keys()

    if checks:
        LOG.debug("Found this consul checks: %s" % checks)
    else:
        LOG.debug("No consul checks found")
    return checks


def get_failed_cluster_checks(con, service_names):
    """
    Returns a dict with all checks where the check status is != passing.
    The service_names parameter is a list of service names.

    If a service has the tag "ignore_maintenance", we ignore the check called
    "_node_maintenance", which is a failing check when the node is in
    maintenance.
    """

    failed_checks = {}
    for service_name in service_names:
        for service_results in con.health.service(service_name)[1]:
            tags = service_results["Service"]["Tags"]
            for check in service_results["Checks"]:
                LOG.info("Service %s check %s on %s. Status: %s",
                         service_name, check["CheckID"], check["Node"], check["Status"])
                if check["Status"] != "passing":
                    if not ignore_maintenance_check(check["CheckID"], tags):
                        failed_checks[check["CheckID"]] = check

    return failed_checks


def ignore_maintenance_check(checkid, tags):
    if tags and "ignore_maintenance" in tags:
        if checkid == "_node_maintenance":
            return True
    return False
