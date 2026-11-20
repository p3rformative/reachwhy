"""Phase 1 DNS rules on small mutations of corpus fixtures (no subscription ids inline)."""
from conftest import hop, resource, run

ZONE = "privatelink.blob.core.windows.net"


def zone_resources(snap):
    return [r for r in snap["resources"] if r["type"].startswith("microsoft.network/privatednszones")]


def link_resource(snap):
    return resource(snap, "microsoft.network/privatednszones/virtualnetworklinks")


def a_record(snap):
    return resource(snap, "microsoft.network/privatednszones/a")


def test_hub_zone_resolves_green_with_app_setting_caveat(hub_case):
    snap, exp = hub_case
    h = hop(run(snap, exp), "dns")
    assert h["state"] == "green"
    assert any("WEBSITE_DNS_SERVER" in c for c in h["caveats"])


def test_policy_absent_is_amber_not_red(hub_case):
    snap, exp = hub_case
    snap["resources"].remove(a_record(snap))
    del link_resource(snap)["properties"]["resolutionPolicy"]
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("amber", "DNS_FALLBACK_UNKNOWN")


def test_record_missing_when_zone_has_other_records(hub_case):
    snap, exp = hub_case
    rec = a_record(snap)
    rec["name"] = "stother-demo"
    rec["id"] = rec["id"].rsplit("/", 1)[0] + "/stother-demo"
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("red", "DNS_RECORD_MISSING")


def test_empty_zone_in_other_subscription_without_fallback_is_red(hub_case):
    snap, exp = hub_case
    snap["resources"].remove(a_record(snap))
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("red", "DNS_ZONE_EMPTY_NO_FALLBACK")


def test_fallback_in_separate_link_resource_is_amber(hub_case):
    snap, exp = hub_case
    snap["resources"].remove(a_record(snap))
    link_resource(snap)["properties"]["resolutionPolicy"] = "NxDomainRedirect"
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("amber", "DNS_FALLBACK_TO_PUBLIC")
    assert any(e["path"] == "properties.publicNetworkAccess" for e in h["evidence"])


def test_fallback_does_not_hide_a_stale_record(hub_case):
    snap, exp = hub_case
    link_resource(snap)["properties"]["resolutionPolicy"] = "NxDomainRedirect"
    a_record(snap)["properties"]["records"][0]["ipv4Address"] = "10.20.9.9"
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("red", "DNS_RECORD_STALE_IP")


def test_zone_not_linked_to_integration_vnet_even_if_linked_elsewhere(hub_case):
    snap, exp = hub_case
    link_resource(snap)["properties"]["virtualNetwork"]["id"] += "-other"
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("red", "DNS_ZONE_NOT_LINKED")


def test_link_match_ignores_id_case(hub_case):
    snap, exp = hub_case
    link_resource(snap)["properties"]["virtualNetwork"]["id"] = link_resource(snap)["properties"]["virtualNetwork"]["id"].upper()
    assert hop(run(snap, exp), "dns")["state"] == "green"


def test_two_same_named_zones_only_the_linked_one_counts(hub_case):
    snap, exp = hub_case
    other = dict(resource(snap, "microsoft.network/privatednszones", ZONE))
    other["id"] = other["id"].replace("rg-hub-demo", "rg-other-demo")
    snap["resources"].append(other)
    assert hop(run(snap, exp), "dns")["state"] == "green"


def test_two_linked_same_named_zones_is_amber_input_incomplete(hub_case):
    snap, exp = hub_case
    zone = resource(snap, "microsoft.network/privatednszones", ZONE)
    other = dict(zone)
    other["id"] = zone["id"].replace("rg-hub-demo", "rg-other-demo")
    snap["resources"].append(other)
    link = dict(link_resource(snap))
    link["id"] = other["id"] + "/virtualnetworklinks/link-vnet-demo"
    snap["resources"].append(link)
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("amber", "DNS_INPUT_INCOMPLETE")


def test_vnet_custom_dns_is_amber(demo_case):
    snap, exp = demo_case
    resource(snap, "microsoft.network/virtualnetworks")["properties"]["dhcpOptions"]["dnsServers"] = ["10.20.9.4"]
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("amber", "DNS_CUSTOM_SERVER")


def test_empty_site_dns_list_does_not_count_as_override(demo_case):
    snap, exp = demo_case
    resource(snap, "microsoft.web/sites")["properties"]["dnsConfiguration"] = {"dnsServers": []}
    assert hop(run(snap, exp), "dns")["code"] == "DNS_ZONE_NOT_LINKED"


def test_unreadable_scope_beats_missing_zone_red(demo_case):
    snap, exp = demo_case
    snap["resources"] = [r for r in snap["resources"] if not r["type"].startswith("microsoft.network/privatednszones")]
    snap["visibility"]["unreadable"] = ["hub-scope-demo"]
    assert hop(run(snap, exp), "dns")["code"] == "DNS_ZONE_NOT_VISIBLE"


def test_missing_integration_is_amber_input_incomplete(demo_case):
    snap, exp = demo_case
    del resource(snap, "microsoft.web/sites")["properties"]["virtualNetworkSubnetId"]
    h = hop(run(snap, exp), "dns")
    assert (h["state"], h["code"]) == ("amber", "DNS_INPUT_INCOMPLETE")


def test_unknown_group_id_is_amber_not_red(demo_case):
    snap, exp = demo_case
    exp = {**exp, "pair": {**exp["pair"], "targetSubresource": "unknown-demo"}}
    pe = resource(snap, "microsoft.network/privateendpoints")
    pe["properties"]["privateLinkServiceConnections"][0]["properties"]["groupIds"] = ["unknown-demo"]
    assert hop(run(snap, exp), "dns")["state"] == "amber"


def test_analysis_does_not_mutate_the_snapshot(hub_case):
    import copy
    snap, exp = hub_case
    before = copy.deepcopy(snap)
    run(snap, exp)
    assert snap == before


def test_verdict_is_marked_partial(demo_case):
    snap, exp = demo_case
    v = run(snap, exp)
    assert v["complete"] is False
    assert set(v["evaluatedHops"]) == {"origin", "dns"}
    assert "rbac" in v["notEvaluated"]
