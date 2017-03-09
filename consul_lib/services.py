import logging

LOG = logging.getLogger(__name__)


def get_relevant_checks(con, tag):
    services = con.agent.services()
    if not services:
        LOG.debug("Unable to find services.")
        return None
    for service in services.values():
        tags = service["Tags"]
        if tags and tag in tags:
            yield service["ID"]


def get_failed_checks(con, relevant_checks):
    checks = con.agent.checks()
    if not checks:
        return None
    for check in checks.values():
        if check["ServiceID"] in relevant_checks and check["Status"] != "passing":
            yield check
