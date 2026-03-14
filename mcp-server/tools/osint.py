"""
osint.py — OSINT enrichment pour les adresses IP.
Adapté de borodino/osint_lookup.py (version async avec httpx).
"""

import ipaddress
import os
import httpx

TIMEOUT = 10
ABUSEIPDB_KEY = os.getenv("ABUSEIPDB_API_KEY")
VIRUSTOTAL_KEY = os.getenv("VIRUSTOTAL_API_KEY")
SHODAN_KEY = os.getenv("SHODAN_API_KEY")


def _is_private(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str.split("/")[0])
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_reserved
            or addr.is_link_local
            or addr.is_multicast
        )
    except ValueError:
        return True


async def _get(client: httpx.AsyncClient, url: str, headers: dict = None) -> dict:
    try:
        r = await client.get(url, headers=headers or {}, timeout=TIMEOUT)
        return r.json()
    except Exception:
        return {}


async def lookup_ip(ip: str) -> dict:
    """
    OSINT complet pour une IP publique.
    Retourne: geolocation, threat_score, threat_level, is_malicious, détails sources.
    """
    if _is_private(ip):
        return {
            "ip": ip,
            "is_private": True,
            "note": "IP privée/réservée — OSINT non applicable",
        }

    result: dict = {"ip": ip, "is_private": False}

    async with httpx.AsyncClient(verify=False) as client:
        # ip-api.com — géo + proxy/VPN
        fields = "status,country,countryCode,region,city,isp,org,as,asname,mobile,proxy,hosting"
        geo = await _get(client, f"http://ip-api.com/json/{ip}?fields={fields}")
        if geo.get("status") == "success":
            result.update({
                "country": geo.get("country"),
                "country_code": geo.get("countryCode"),
                "city": geo.get("city"),
                "isp": geo.get("isp"),
                "asn": geo.get("as"),
                "is_proxy": bool(geo.get("proxy")),
                "is_hosting": bool(geo.get("hosting")),
                "is_mobile": bool(geo.get("mobile")),
            })

        # AlienVault OTX
        otx_gen = await _get(client, f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general")
        otx_mal = await _get(client, f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/malware")
        result["otx_pulses"] = otx_gen.get("pulse_info", {}).get("count", 0)
        result["malware_samples"] = len(otx_mal.get("data", []))

        # ThreatCrowd
        tc = await _get(client, f"https://www.threatcrowd.org/searchApi/v2/ip/report/?ip={ip}")
        if tc.get("response_code") == "1":
            result["threatcrowd_votes"] = int(tc.get("votes", 0))
            result["threatcrowd_hashes"] = len(tc.get("hashes", []))

        # AbuseIPDB (optionnel)
        if ABUSEIPDB_KEY:
            ab = await _get(
                client,
                f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90",
                headers={"Key": ABUSEIPDB_KEY, "Accept": "application/json"},
            )
            d = ab.get("data", {})
            result["abuse_reports"] = d.get("totalReports", 0)
            result["abuse_confidence"] = d.get("abuseConfidenceScore", 0)
            result["is_tor"] = bool(d.get("isTor", False))

        # VirusTotal (optionnel)
        if VIRUSTOTAL_KEY:
            vt = await _get(
                client,
                f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
                headers={"x-apikey": VIRUSTOTAL_KEY},
            )
            stats = vt.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            result["vt_malicious"] = stats.get("malicious", 0) + stats.get("suspicious", 0)

        # Shodan (optionnel)
        if SHODAN_KEY:
            sh = await _get(client, f"https://api.shodan.io/shodan/host/{ip}?key={SHODAN_KEY}")
            result["shodan_vulns"] = list(sh.get("vulns", []))

    # Calcul du score
    score = 0
    if result.get("is_tor"):
        score += 30
    elif result.get("is_proxy"):
        score += 10
    if result.get("is_hosting"):
        score += 5
    score += min(result.get("abuse_reports", 0) * 3, 30)
    score += min(result.get("abuse_confidence", 0) // 10, 10)
    malware = result.get("malware_samples", 0) + result.get("vt_malicious", 0)
    score += min(malware * 5, 25)
    score += min(result.get("otx_pulses", 0) * 2, 15)
    votes = result.get("threatcrowd_votes", 0)
    if votes < 0:
        score += min(abs(votes) * 5, 20)

    score = min(score, 100)
    if score >= 70:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 30:
        level = "medium"
    elif score >= 10:
        level = "low"
    else:
        level = "clean"

    result["threat_score"] = score
    result["threat_level"] = level
    result["is_malicious"] = score >= 30

    return result
