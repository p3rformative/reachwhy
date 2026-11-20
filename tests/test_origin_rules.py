"""Phase 1 origin rule: application routing (outboundVnetRouting / vnetRouteAllEnabled)."""
import pytest

from conftest import hop, resource, run


def set_routing(snap, new=None, legacy=None, legacy_in_siteconfig=False):
    p = resource(snap, "microsoft.web/sites")["properties"]
    p.pop("vnetRouteAllEnabled", None)
    p.pop("outboundVnetRouting", None)
    if new is not None:
        p["outboundVnetRouting"] = new
    if legacy is not None:
        if legacy_in_siteconfig:
            p["siteConfig"] = {"vnetRouteAllEnabled": legacy}
        else:
            p["vnetRouteAllEnabled"] = legacy


@pytest.mark.parametrize("new", [{"allTraffic": True}, {"applicationTraffic": True},
                                 {"allTraffic": False, "applicationTraffic": True}])
def test_new_properties_enabling_routing_are_green(hub_case, new):
    snap, exp = hub_case
    set_routing(snap, new=new)
    assert hop(run(snap, exp), "origin")["state"] == "green"


def test_legacy_property_still_counts_top_level_and_site_config(hub_case):
    snap, exp = hub_case
    for in_site_config in (False, True):
        set_routing(snap, legacy=True, legacy_in_siteconfig=in_site_config)
        h = hop(run(snap, exp), "origin")
        assert h["state"] == "green" and "private (RFC1918)" not in h["cause"]


def test_routing_off_with_public_resolution_is_amber_never_red(demo_case):
    snap, exp = demo_case
    set_routing(snap, new={"allTraffic": False})
    v = run(snap, exp)
    h = hop(v, "origin")
    assert (h["state"], h["code"]) == ("amber", "ORIGIN_ROUTE_ALL_OFF")
    assert v["firstRedHop"] == "dns"


def test_routing_off_with_private_resolution_is_green(hub_case):
    snap, exp = hub_case
    set_routing(snap, new={"allTraffic": False})
    assert hop(run(snap, exp), "origin")["state"] == "green"


def test_new_and_legacy_that_disagree_are_amber_conflict(hub_case):
    snap, exp = hub_case
    set_routing(snap, new={"allTraffic": True}, legacy=False)
    h = hop(run(snap, exp), "origin")
    assert (h["state"], h["code"]) == ("amber", "ORIGIN_ROUTE_CONFLICT")


def test_new_and_legacy_that_agree_are_not_a_conflict(hub_case):
    snap, exp = hub_case
    set_routing(snap, new={"allTraffic": True}, legacy=True)
    assert hop(run(snap, exp), "origin")["state"] == "green"


def test_no_routing_properties_is_amber_unknown(hub_case):
    snap, exp = hub_case
    set_routing(snap)
    h = hop(run(snap, exp), "origin")
    assert (h["state"], h["code"]) == ("amber", "ORIGIN_ROUTING_UNKNOWN")


def test_evidence_cites_the_property_read(hub_case):
    snap, exp = hub_case
    set_routing(snap, new={"allTraffic": True})
    paths = [e["path"] for e in hop(run(snap, exp), "origin")["evidence"]]
    assert "properties.outboundVnetRouting" in paths
