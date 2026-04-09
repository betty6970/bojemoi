#!/usr/bin/env python3
"""
osint_lookup.py - Synchronous OSINT enrichment for IP addresses.
Used by thearm_bm12 to enrich host records with threat intelligence.

Sources (no API key needed):
  - ip-api.com     : geolocation, proxy/VPN/hosting detection
  - AlienVault OTX : malware samples, threat pulses
  - ThreatCrowd    : malicious votes, hashes

Sources (optional, via env vars):
  - AbuseIPDB  (ABUSEIPDB_API_KEY)  : abuse reports + confidence score
  - VirusTotal (VIRUSTOTAL_API_KEY) : malware engine detections
  - Shodan     (SHODAN_API_KEY)     : open ports + CVEs
"""

import ipaddress
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

TIMEOUT = 10  # seconds per request


def _read_secret(name, legacy_env=None):
    """Read sensitive value: legacy env var → NAME env var → /run/secrets/name file."""
    if legacy_env:
        v = os.getenv(legacy_env, "")
        if v:
            return v
    v = os.getenv(name.upper(), "")
    if v:
        return v
    try:
        with open(f"/run/secrets/{name}") as f:
            return f.read().strip()
    except OSError:
        return ""


ABUSEIPDB_KEY   = _read_secret("abuseipdb_api_key", "ABUSEIPDB_API_KEY") or None
VIRUSTOTAL_KEY  = _read_secret("virustotal_api_key", "VIRUSTOTAL_API_KEY") or None
SHODAN_KEY      = _read_secret("shodan_api_key", "SHODAN_API_KEY") or None


def _is_private(ip_str: str) -> bool:
    """Returns True if the IP is private/reserved (skip OSINT)."""
    try:
        addr = ipaddress.ip_address(ip_str.split("/")[0])
        return (
            addr.is_private or addr.is_loopback
            or addr.is_reserved or addr.is_link_local
            or addr.is_multicast
        )
    except ValueError:
        return True


def _get(url: str, headers: dict = None) -> dict:
    """HTTP GET with timeout, returns parsed JSON or empty dict on error."""
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _fetch_ip_api(ip: str) -> dict:
    """ip-api.com — free, no key. Geo + proxy/VPN/hosting detection."""
    fields = ("status,country,countryCode,region,city,"
              "isp,org,as,asname,mobile,proxy,hosting")
    data = _get(f"http://ip-api.com/json/{ip}?fields={fields}")
    if data.get("status") != "success":
        return {}
    return {
        "country":      data.get("country"),
        "country_code": data.get("countryCode"),
        "isp":          data.get("isp"),
        "asn":          data.get("as"),
        "is_proxy":     bool(data.get("proxy")),
        "is_hosting":   bool(data.get("hosting")),
        "is_mobile":    bool(data.get("mobile")),
    }


def _fetch_otx(ip: str) -> dict:
    """AlienVault OTX — free, no key. Malware samples + threat pulses."""
    general = _get(f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general")
    malware = _get(f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/malware")
    return {
        "otx_pulses":     general.get("pulse_info", {}).get("count", 0),
        "malware_samples": len(malware.get("data", [])),
    }


def _fetch_threatcrowd(ip: str) -> dict:
    """ThreatCrowd — free, no key. Malicious votes + hash count."""
    data = _get(f"https://www.threatcrowd.org/searchApi/v2/ip/report/?ip={ip}")
    if data.get("response_code") != "1":
        return {}
    return {
        "threatcrowd_votes":  int(data.get("votes", 0)),  # négatif = malveillant
        "threatcrowd_hashes": len(data.get("hashes", [])),
    }


def _fetch_abuseipdb(ip: str) -> dict:
    """AbuseIPDB — requires ABUSEIPDB_API_KEY."""
    if not ABUSEIPDB_KEY:
        return {}
    data = _get(
        f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90",
        headers={"Key": ABUSEIPDB_KEY, "Accept": "application/json"},
    )
    d = data.get("data", {})
    return {
        "abuse_reports":    d.get("totalReports", 0),
        "abuse_confidence": d.get("abuseConfidenceScore", 0),
        "is_tor":           bool(d.get("isTor", False)),
    }


def _fetch_virustotal(ip: str) -> dict:
    """VirusTotal — requires VIRUSTOTAL_API_KEY."""
    if not VIRUSTOTAL_KEY:
        return {}
    data = _get(
        f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
        headers={"x-apikey": VIRUSTOTAL_KEY},
    )
    stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
    return {
        "vt_malicious": stats.get("malicious", 0) + stats.get("suspicious", 0),
    }


def _fetch_shodan(ip: str) -> dict:
    """Shodan — requires SHODAN_API_KEY. CVEs + open ports."""
    if not SHODAN_KEY:
        return {}
    data = _get(f"https://api.shodan.io/shodan/host/{ip}?key={SHODAN_KEY}")
    return {
        "vulnerabilities": list(data.get("vulns", [])),
    }


def _calculate_score(r: dict) -> tuple:
    """Calcule le threat_score (0-100) et le niveau."""
    score = 0

    # Proxy / VPN / Tor
    if r.get("is_tor"):
        score += 30
    elif r.get("is_proxy"):
        score += 10
    if r.get("is_hosting"):
        score += 5

    # Abuse reports (AbuseIPDB)
    score += min(r.get("abuse_reports", 0) * 3, 30)
    score += min(r.get("abuse_confidence", 0) // 10, 10)

    # Malware (OTX + VirusTotal)
    malware = r.get("malware_samples", 0) + r.get("vt_malicious", 0)
    score += min(malware * 5, 25)

    # OTX threat pulses
    score += min(r.get("otx_pulses", 0) * 2, 15)

    # ThreatCrowd votes négatifs = malveillant
    votes = r.get("threatcrowd_votes", 0)
    if votes < 0:
        score += min(abs(votes) * 5, 20)

    # CVEs (Shodan)
    score += min(len(r.get("vulnerabilities", [])) * 4, 20)

    score = min(score, 100)

    if score >= 70:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"
    elif score > 0:
        level = "low"
    else:
        level = "clean"

    return score, level


def osint_lookup(ip_str: str) -> dict:
    """
    Effectue un enrichissement OSINT pour une adresse IP.
    Retourne un dict avec threat_score, threat_level et toutes les données.
    Retourne {"threat_score": 0, "threat_level": "clean", "skipped": True}
    pour les IPs privées/réservées.
    """
    ip = ip_str.split("/")[0].strip()

    if _is_private(ip):
        return {"threat_score": 0, "threat_level": "clean", "skipped": True}

    print(f"  [OSINT] Lookup {ip}...", flush=True)
    result = {"ip": ip, "timestamp": datetime.utcnow().isoformat()}

    # APIs gratuites (pas de clé)
    result.update(_fetch_ip_api(ip))
    result.update(_fetch_otx(ip))
    result.update(_fetch_threatcrowd(ip))

    # APIs optionnelles (clé via env var)
    result.update(_fetch_abuseipdb(ip))
    result.update(_fetch_virustotal(ip))
    result.update(_fetch_shodan(ip))

    score, level = _calculate_score(result)
    result["threat_score"] = score
    result["threat_level"] = level
    result["is_malicious"] = score >= 50

    flag = "⚠ MALICIOUS" if result["is_malicious"] else "OK"
    print(f"  [OSINT] {ip} → score={score} ({level}) {flag}", flush=True)

    return result
