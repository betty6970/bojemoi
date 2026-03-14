"""
nmap.py — Exécution de scans nmap depuis le MCP server.
"""

import asyncio
import re
import shlex


SCAN_TYPES = {
    "basic":   ["-sV", "--version-intensity", "5"],
    "full":    ["-sV", "-sC", "-O", "--version-intensity", "9"],
    "stealth": ["-sS", "-sV", "--version-intensity", "3"],
    "udp":     ["-sU", "--top-ports", "100"],
    "quick":   ["-T4", "-F"],
}

# Limite de sécurité : pas de scan de plages /8 ou /16 complètes
_MAX_CIDR = 24


def _validate_target(target: str) -> bool:
    """Refuse les cibles trop larges ou invalides."""
    import ipaddress
    target = target.strip()
    # CIDR notation
    if "/" in target:
        try:
            net = ipaddress.ip_network(target, strict=False)
            if net.prefixlen < _MAX_CIDR:
                return False
        except ValueError:
            return False
    # Range avec tiret ex. 192.168.1.1-50
    if re.search(r'\d+-\d+', target):
        return True
    # Single IP ou hostname
    return bool(re.match(r'^[\w.\-:]+$', target))


async def run_nmap(
    target: str,
    ports: str = None,
    scan_type: str = "basic",
    timeout: int = 120,
) -> dict:
    """
    Lance nmap sur la cible.
    scan_type: basic | full | stealth | udp | quick
    ports: '80,443,8080' ou '1-1000' (None = top 1000)
    Retourne: {success, command, output, hosts_found}
    """
    if not _validate_target(target):
        return {
            "success": False,
            "error": f"Cible refusée : CIDR trop large ou format invalide ({target})",
        }

    flags = SCAN_TYPES.get(scan_type, SCAN_TYPES["basic"])
    cmd = ["nmap"] + flags

    if ports:
        cmd += ["-p", ports]

    cmd += ["-oN", "-", target]  # output normal sur stdout

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        output = stdout.decode(errors="replace")
        hosts_found = len(re.findall(r"Host:\s+\S+", output))

        return {
            "success": proc.returncode == 0,
            "command": " ".join(cmd),
            "output": output[:8000],  # limite pour éviter surcharge LLM
            "hosts_found": hosts_found,
            "stderr": stderr.decode(errors="replace")[:500] if stderr else "",
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Timeout après {timeout}s",
            "command": " ".join(cmd),
        }
    except FileNotFoundError:
        return {"success": False, "error": "nmap non trouvé dans le PATH"}
    except Exception as e:
        return {"success": False, "error": str(e)}
