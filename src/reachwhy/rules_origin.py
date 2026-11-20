"""Origin hop (phase 1): application routing (route all) of the site. Other origin rules
(VNet integration present, subnet delegation, Container Apps) are not implemented yet."""
from __future__ import annotations

from .model import AMBER, GREEN, Hop, evidence
from .snapshot import Snapshot

SRC_ROUTING = "https://learn.microsoft.com/en-us/azure/app-service/configure-vnet-integration-routing"
SRC_OVERVIEW = "https://learn.microsoft.com/en-us/azure/app-service/overview-vnet-integration"


def application_routing(props: dict) -> tuple[bool | None, list[dict], bool]:
    """(routed, evidence, conflict). `routed` is True when application traffic goes through the VNet:
    outboundVnetRouting.allTraffic or .applicationTraffic is true. The legacy vnetRouteAllEnabled
    (top level or under siteConfig) is used when the new property is absent. The docs do not state
    which one wins if both exist and disagree, so that is reported as a conflict."""
    ev: list[dict] = []
    new_vals = {k: v for k, v in (props.get("outboundVnetRouting") or {}).items()
                if k in ("allTraffic", "applicationTraffic") and isinstance(v, bool)}
    legacy = props.get("vnetRouteAllEnabled")
    if legacy is None:
        legacy = (props.get("siteConfig") or {}).get("vnetRouteAllEnabled")
    new = any(new_vals.values()) if new_vals else None
    if new_vals:
        ev.append({"path": "properties.outboundVnetRouting", "value": new_vals})
    if isinstance(legacy, bool):
        ev.append({"path": "properties.vnetRouteAllEnabled", "value": legacy})
    if new is not None and isinstance(legacy, bool):
        return new, ev, new != legacy
    if new is not None:
        return new, ev, False
    if isinstance(legacy, bool):
        return legacy, ev, False
    return None, ev, False


def check_origin_routing(snap: Snapshot, origin_id: str, dns_hop: Hop | None) -> Hop:
    origin = snap.get(origin_id)
    if origin is None:
        return Hop("origin", AMBER, "ORIGIN_INPUT_INCOMPLETE", "The origin is not in the snapshot.", [], [],
                   why_unverifiable="Origin missing from the snapshot.", how_to_verify="Provide the origin resource.")
    routed, raw_ev, conflict = application_routing(origin.get("properties") or {})
    ev = [evidence(origin["id"], e["path"], e["value"]) for e in raw_ev]
    src = [SRC_ROUTING, SRC_OVERVIEW]
    verify = "Read properties.outboundVnetRouting of the site (az resource show) and compare with the legacy vnetRouteAllEnabled."
    if conflict:
        return Hop("origin", AMBER, "ORIGIN_ROUTE_CONFLICT",
                   "outboundVnetRouting and the legacy vnetRouteAllEnabled disagree, and the documentation does not say which one wins.",
                   ev, src, why_unverifiable="Precedence between the new and the legacy property is not documented.",
                   how_to_verify=verify)
    if routed is None:
        return Hop("origin", AMBER, "ORIGIN_ROUTING_UNKNOWN",
                   "Neither outboundVnetRouting nor vnetRouteAllEnabled is present, so application routing is unknown.",
                   ev, src, why_unverifiable="Routing properties are absent (the WEBSITE_VNET_ROUTE_ALL app setting is not readable with Reader).",
                   how_to_verify=verify)
    if routed:
        return Hop("origin", GREEN, None, "Application traffic is routed through the VNet integration.", ev, src,
                   caveats=["Only application routing was evaluated; VNet integration and subnet delegation are not evaluated yet."])
    # Route all is off: only RFC1918 traffic and service endpoints enter the VNet.
    if dns_hop is not None and dns_hop.state != GREEN:
        return Hop("origin", AMBER, "ORIGIN_ROUTE_ALL_OFF",
                   "Application routing is off, so only private (RFC1918) traffic enters the VNet; the DNS hop does not "
                   "show the name resolving to a private IP, so traffic to it goes out directly from the app.",
                   ev, src, why_unverifiable="With routing off, internet-bound traffic leaves the app directly and is not subject to the VNet's NSGs and routes.",
                   how_to_verify="Enable outbound internet traffic routing (outboundVnetRouting.applicationTraffic or allTraffic) or fix the DNS hop.")
    return Hop("origin", GREEN, None,
               "Application routing is off, but the name resolves to a private IP and private (RFC1918) traffic enters the VNet.",
               ev, src, caveats=["Only application routing was evaluated; VNet integration and subnet delegation are not evaluated yet."])
