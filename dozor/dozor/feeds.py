from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

import httpx

from .metrics import feeds_total, ips_by_feed

log = logging.getLogger(__name__)


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
                ips = parser(resp.text)
                results[name] = ips
                feeds_total.labels(feed=name, status="ok").inc()
                ips_by_feed.labels(feed=name).set(len(ips))
                log.info("feed %s: %d IPs/CIDRs", name, len(ips))
            except Exception:
                feeds_total.labels(feed=name, status="error").inc()
                log.exception("failed to download feed %s", name)
    return results
