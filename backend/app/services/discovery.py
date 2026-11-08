import concurrent.futures
import ipaddress
import subprocess

from app.services import snmp_service


def ping_host(ip: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def scan_subnet(subnet: str, workers: int = 64) -> list[str]:
    network = ipaddress.ip_network(subnet, strict=False)
    hosts = [str(host) for host in network.hosts()]
    live: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(ping_host, hosts)
        for ip, is_up in zip(hosts, results):
            if is_up:
                live.append(ip)
    return live


def probe(ip: str, community: str = "public") -> dict:
    data = snmp_service.poll(ip, community)
    return {
        "ip_address": ip,
        "reachable": data.get("reachable") == "yes",
        "hostname": data.get("sysName"),
        "sysDescr": data.get("sysDescr"),
        "vendor": data.get("vendor"),
        "guessed_type": data.get("guessed_type", "other"),
        "model": data.get("model"),
        "serial": data.get("serial"),
    }
