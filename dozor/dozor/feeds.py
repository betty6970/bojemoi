from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

import httpx

from .metrics import feeds_total, ips_by_feed

log = logging.getLogger(__name__)

# Private/reserved ranges to exclude — these overlap with HOME_NET and Docker networks
_PRIVATE_NETS = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("100.64.0.0/10"),   # CGNAT
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("224.0.0.0/4"),      # multicast
    ipaddress.IPv4Network("240.0.0.0/4"),      # reserved
    ipaddress.IPv4Network("255.255.255.255/32"),
]


def _is_private(s: str) -> bool:
    """Return True if IP/CIDR overlaps with private/reserved ranges."""
    try:
        if "/" in s:
            net = ipaddress.IPv4Network(s, strict=False)
            return any(net.overlaps(p) for p in _PRIVATE_NETS)
        else:
            addr = ipaddress.IPv4Address(s)
            return any(addr in p for p in _PRIVATE_NETS)
    except (ValueError, ipaddress.AddressValueError):
        return False


def _valid_ip_or_cidr(s: str) -> bool:
    """Return True if s is a valid IPv4 address or CIDR."""
    try:
        if "/" in s:
            ipaddress.IPv4Network(s, strict=False)
        else:
            ipaddress.IPv4Address(s)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def _parse_netset(text: str) -> set[str]:
    """Parse FireHOL .netset format — one IP or CIDR per line, # comments."""
    results: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if _valid_ip_or_cidr(line):
            results.add(line)
    return results


def _parse_threatfox_csv(text: str) -> set[str]:
    """Parse ThreatFox CSV — fields are quoted, ip:port in column index 2."""
    results: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        ip_port = parts[2].strip().strip('" ')
        ip = ip_port.split(":")[0].strip()
        if _valid_ip_or_cidr(ip):
            results.add(ip)
    return results


def _parse_urlhaus(text: str) -> set[str]:
    """Parse URLhaus online URLs — extract hostnames that are IPs."""
    results: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            parsed = urlparse(line)
            host = parsed.hostname or ""
            if _valid_ip_or_cidr(host):
                results.add(host)
        except Exception:
            continue
    return results


def _parse_plain_ip(text: str) -> set[str]:
    """Parse plain IP list — one IP per line, # comments."""
    results: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if _valid_ip_or_cidr(line):
            results.add(line)
    return results


_PARSERS = {
    "netset": _parse_netset,
    "threatfox_csv": _parse_threatfox_csv,
    "urlhaus": _parse_urlhaus,
    "plain_ip": _parse_plain_ip,
}


async def download_feeds(
    feeds: list[dict[str, str]],
) -> dict[str, set[str]]:
    """Download all feeds, return {feed_name: set_of_ips}."""
    results: dict[str, set[str]] = {}
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for feed in feeds:
            name = feed["name"]
            url = feed["url"]
            parser = _PARSERS.get(feed["parser"])
            if parser is None:
                log.error("unknown parser %s for feed %s", feed["parser"], name)
                continue
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                raw_ips = parser(resp.text)
                ips = {ip for ip in raw_ips if not _is_private(ip)}
                filtered = len(raw_ips) - len(ips)
                if filtered:
                    log.info("feed %s: filtered %d private/reserved IPs", name, filtered)
                results[name] = ips
                feeds_total.labels(feed=name, status="ok").inc()
                ips_by_feed.labels(feed=name).set(len(ips))
                log.info("feed %s: %d IPs/CIDRs", name, len(ips))
            except Exception:
                feeds_total.labels(feed=name, status="error").inc()
                log.exception("failed to download feed %s", name)
    return results
