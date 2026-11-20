"""DNS hop (phase 1): zone visibility across subscriptions, link, record, fallback to internet,
and DNS server overrides. Every rule rests on a source cited in docs/design.md."""
from __future__ import annotations

from .model import AMBER, GREEN, RED, Hop, evidence
from .snapshot import LINKS, ZONE_A, ZONES, Snapshot, norm, vnet_of_subnet

SRC_FALLBACK = "https://learn.microsoft.com/en-us/azure/dns/private-dns-fallback"
SRC_ARG = "https://learn.microsoft.com/en-us/azure/dns/private-dns-arg"
SRC_NAMERES = "https://learn.microsoft.com/en-us/azure/app-service/overview-name-resolution"
SRC_ZONES = "https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-dns"

# Public Private Link zone names per private endpoint group id.
ZONE_BY_GROUP = {
    "blob": "privatelink.blob.core.windows.net",
    "file": "privatelink.file.core.windows.net",
    "queue": "privatelink.queue.core.windows.net",
    "table": "privatelink.table.core.windows.net",
    "dfs": "privatelink.dfs.core.windows.net",
    "vault": "privatelink.vaultcore.azure.net",
    "sqlserver": "privatelink.database.windows.net",
}


def _amber(code: str, cause: str, why: str, fqdn: str | None, ev=None, sources=None) -> Hop:
    how = (f"From a VM inside the integration VNet: Resolve-DnsName {fqdn} -Type A | "
           "Select-Object Name, IPAddress  (expect a private IP of the endpoint)") if fqdn else \
        "Provide the missing data in the snapshot."
    return Hop("dns", AMBER, code, cause, ev or [], sources or [SRC_ZONES], why_unverifiable=why, how_to_verify=how)


def _incomplete(why: str, fqdn: str | None = None) -> Hop:
    return _amber("DNS_INPUT_INCOMPLETE", "The DNS hop cannot be evaluated: " + why, why, fqdn)


def _find_private_endpoint(snap: Snapshot, target_id: str, subresource: str) -> dict | None:
    for pe in snap.of_type("microsoft.network/privateendpoints"):
        for c in (pe.get("properties") or {}).get("privateLinkServiceConnections", []):
            p = c.get("properties") or {}
            if norm(p.get("privateLinkServiceId")) == norm(target_id) and \
                    subresource.lower() in [g.lower() for g in p.get("groupIds", [])]:
                return pe
    return None


def _links_of(snap: Snapshot, zone: dict) -> list[dict]:
    """Links of a zone, from inline `virtualNetworkLinks` and/or separate link resources."""
    out = []
    for l in zone.get("virtualNetworkLinks", []) or []:
        out.append({"resource": zone["id"], "path": "virtualNetworkLinks", "props": l.get("properties") or {}})
    prefix = norm(zone["id"]) + "/virtualnetworklinks/"
    for r in snap.of_type(LINKS):
        if norm(r.get("id")).startswith(prefix):
            out.append({"resource": r["id"], "path": "properties", "props": r.get("properties") or {}})
    return out


def _a_records(snap: Snapshot, zone: dict) -> dict[str, list[str]]:
    """A records by name, from inline `recordSets` and/or Resource Graph `dnsresources` rows."""
    recs: dict[str, list[str]] = {}
    for rs in zone.get("recordSets", []) or []:
        if str(rs.get("type", "")).upper() == "A":
            recs.setdefault(norm(rs.get("name")), []).extend(rs.get("aRecords", []))
    prefix = norm(zone["id"]) + "/a/"
    for r in snap.of_type(ZONE_A):
        if norm(r.get("id")).startswith(prefix):
            ips = [x.get("ipv4Address") for x in (r.get("properties") or {}).get("records", [])]
            recs.setdefault(norm(r.get("name")), []).extend(i for i in ips if i)
    return recs


def _visibility_gap(snap: Snapshot, zone_name: str, fqdn: str, ev: list[dict]) -> Hop | None:
    """Amber DNS_ZONE_NOT_VISIBLE when an absent zone or link may simply be outside what was read.
    A red "missing" or "not linked" needs a snapshot that declares its visibility and has no unreadable scope."""
    declared = (snap.data.get("visibility") or {}).get("unreadable")
    if snap.has_unreadable_scope:
        why = "A subscription or scope that may hold the zone or its link (for example a hub) is not readable."
        cause = f"Zone {zone_name} or its link to the integration VNet may be in a scope that is not readable."
    elif not snap.visibility_declared:
        why = ("The snapshot does not declare which subscriptions were read (visibility.subscriptions and "
               "visibility.unreadable), so an absent zone or link cannot be told apart from one outside the readable scope.")
        cause = f"The snapshot does not declare its visibility, so the absence of zone {zone_name} or of its link is not conclusive."
    else:
        return None
    return _amber("DNS_ZONE_NOT_VISIBLE", cause, why, fqdn,
                  ev + [evidence("visibility", "unreadable", declared, "declared")], [SRC_ARG])


APP_SETTINGS_CAVEAT = ("App settings WEBSITE_DNS_SERVER and WEBSITE_DNS_ALT_SERVER are not readable with Reader: "
                       "this verdict assumes they are not set; only the site property dnsConfiguration was checked.")


def check_dns(snap: Snapshot, origin_id: str, target_id: str, subresource: str) -> Hop:
    """DNS hop. Every verdict, red included, carries the Reader caveat about app settings."""
    h = _check_dns(snap, origin_id, target_id, subresource)
    h.caveats.append(APP_SETTINGS_CAVEAT)
    return h


def _check_dns(snap: Snapshot, origin_id: str, target_id: str, subresource: str) -> Hop:
    origin = snap.get(origin_id)
    target = snap.get(target_id)
    if origin is None or target is None:
        return _incomplete("origin or target is not in the snapshot")
    vnet_id = vnet_of_subnet((origin.get("properties") or {}).get("virtualNetworkSubnetId"))
    if vnet_id is None:
        return _incomplete("the origin has no virtualNetworkSubnetId (no VNet integration read)")
    vnet = snap.get(vnet_id)
    if vnet is None:
        return _incomplete("the integration VNet is not in the snapshot")
    pe = _find_private_endpoint(snap, target_id, subresource)
    if pe is None:
        return _incomplete(f"no private endpoint for group '{subresource}' of the target is in the snapshot")
    cfgs = (pe.get("properties") or {}).get("customDnsConfigs") or []
    if not cfgs or not cfgs[0].get("fqdn") or not cfgs[0].get("ipAddresses"):
        return _incomplete("the private endpoint has no customDnsConfigs (FQDN and IP)")
    fqdn, pe_ips = cfgs[0]["fqdn"], cfgs[0]["ipAddresses"]
    zone_name = ZONE_BY_GROUP.get(subresource.lower())
    if zone_name is None:
        return _incomplete(f"no known private DNS zone name for group '{subresource}'", fqdn)

    # DNS server overrides: the chain cannot be evaluated from the control plane (design: amber).
    site_dns = ((origin.get("properties") or {}).get("dnsConfiguration") or {}).get("dnsServers") or []
    if site_dns:
        return _amber("DNS_CUSTOM_SERVER",
                      f"The app overrides its DNS servers (dnsConfiguration.dnsServers = {site_dns}); "
                      "the resolution chain is not evaluated.",
                      "A site-level DNS server list overrides the VNet DNS configuration and its answers are not readable.",
                      fqdn, [evidence(origin["id"], "properties.dnsConfiguration.dnsServers", site_dns)], [SRC_NAMERES])
    vnet_dns = ((vnet.get("properties") or {}).get("dhcpOptions") or {}).get("dnsServers") or []
    if vnet_dns:
        return _amber("DNS_CUSTOM_SERVER",
                      f"The integration VNet uses custom DNS servers ({vnet_dns}); the resolution chain is not evaluated.",
                      "Custom DNS servers may forward correctly; that is not readable from the control plane.",
                      fqdn, [evidence(vnet["id"], "properties.dhcpOptions.dnsServers", vnet_dns)], [SRC_NAMERES])

    zones = [z for z in snap.of_type(ZONES) if norm(z.get("name")) == zone_name]
    if not zones:
        gap = _visibility_gap(snap, zone_name, fqdn, [])
        if gap is not None:
            return gap
        return Hop("dns", RED, "DNS_ZONE_MISSING",
                   f"Zone {zone_name} does not exist in any subscription the snapshot declares as read and no custom "
                   f"DNS server is used: {fqdn} resolves to its public IP.",
                   [evidence("snapshot", "resources[type=privatednszones]", []),
                    evidence("visibility", "unreadable", (snap.data.get("visibility") or {}).get("unreadable"), "declared")],
                   [SRC_ARG, SRC_ZONES])

    linked = []
    for z in zones:
        for l in _links_of(snap, z):
            if norm((l["props"].get("virtualNetwork") or {}).get("id")) == norm(vnet_id):
                linked.append((z, l))
    if not linked:
        z0 = zones[0]
        ev_links = [evidence(z0["id"], "virtualNetworkLinks", [_vn(l) for l in _links_of(snap, z0)])]
        gap = _visibility_gap(snap, zone_name, fqdn, ev_links)
        if gap is not None:
            return gap
        return Hop("dns", RED, "DNS_ZONE_NOT_LINKED",
                   f"Zone {zone_name} is not linked to {vnet['name']} (integration VNet of {origin['name']}): "
                   f"{fqdn} resolves to its public IP.",
                   ev_links, [SRC_ZONES])
    if len(linked) > 1:
        return _incomplete(f"more than one zone named {zone_name} is linked to the integration VNet", fqdn)
    zone, link = linked[0]
    policy = norm(link["props"].get("resolutionPolicy"))
    records = _a_records(snap, zone)
    label = fqdn.split(".")[0].lower()
    ev_link = evidence(link["resource"], link["path"] + ".resolutionPolicy", link["props"].get("resolutionPolicy"))

    if label not in records:
        ev = [evidence(zone["id"], "A records", sorted(records)), ev_link]
        if policy == "nxdomainredirect":
            return _amber("DNS_FALLBACK_TO_PUBLIC",
                          f"Zone {zone_name} is linked but has no A record for {label}; the link has fallback to internet "
                          "(NxDomainRedirect), so the name is retried through public recursion and resolves to a public IP. "
                          "Whether that is reachable depends on the target's public network access.",
                          "The result depends on the target's public network access (target-net hop, not evaluated here).",
                          fqdn, ev + [evidence(target["id"], "properties.publicNetworkAccess",
                                               (target.get("properties") or {}).get("publicNetworkAccess"))],
                          [SRC_FALLBACK])
        if policy != "default":
            return _amber("DNS_FALLBACK_UNKNOWN",
                          f"Zone {zone_name} is linked but has no A record for {label}, and the link does not state its "
                          "resolutionPolicy.",
                          "resolutionPolicy is not in the snapshot (it exists from API version 2024-06-01).",
                          fqdn, ev, [SRC_FALLBACK])
        code = "DNS_ZONE_EMPTY_NO_FALLBACK" if not records else "DNS_RECORD_MISSING"
        return Hop("dns", RED, code,
                   f"Zone {zone_name} is linked to {vnet['name']} but has no A record for {label} and the link has no "
                   f"fallback to internet: the query for {fqdn} returns NXDOMAIN.",
                   ev, [SRC_FALLBACK, SRC_ZONES])

    ips = records[label]
    ev = [evidence(zone["id"], f"A record {label}", ips)]
    if not set(ips) & set(pe_ips):
        return Hop("dns", RED, "DNS_RECORD_STALE_IP",
                   f"The A record for {label} points to {ips} but the private endpoint is at {pe_ips}.",
                   ev + [evidence(pe["id"], "properties.customDnsConfigs[0].ipAddresses", pe_ips)], [SRC_ZONES])
    return Hop("dns", GREEN, None,
               f"{fqdn} resolves through zone {zone_name} (linked to {vnet['name']}) to the endpoint IP {pe_ips[0]}.",
               ev + [evidence(pe["id"], "properties.customDnsConfigs[0].ipAddresses", pe_ips)], [SRC_ZONES])


def _vn(link: dict) -> str | None:
    return (link["props"].get("virtualNetwork") or {}).get("id")
