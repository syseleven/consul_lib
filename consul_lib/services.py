import logging

LOG = logging.getLogger(__name__)


def get_local_checks(con, tags=[]):
    """
    Returns a list with all checks for this agent (local checks).
    If tags is provided only checks are returned which have at least on tag in common.
    """

    if tags:
        checks = [k for k, v in con.agent.services().items() if v["Tags"] and set(tags).intersection( (set(v["Tags"])))]
    else:
        checks = con.agent.services().keys()

    if checks:
        LOG.debug("Found this consul checks: %s" % checks)
    else:
        LOG.debug("No consul checks found")
    return checks


def get_failed_cluster_checks(con, checks):
    """
    Returns a dict with all checks where the check status is != passing.
    The checks parameter is a list of service names
    """

    failed_checks = {}
    for service in checks:
        for node in con.health.service(service)[1]:
            for check in node["Checks"]:
                LOG.info("Check %s on %s. Status: %s" % (check["CheckID"], check["Node"], check["Status"]))
                if check["Status"] != "passing":
                    failed_checks[check["CheckID"]]=check

    return failed_checks
