import asyncio

from app.config import settings

OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
OID_IF_NUMBER = "1.3.6.1.2.1.2.1.0"
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_HR_PROCESSOR_LOAD = "1.3.6.1.2.1.25.3.3.1.2"
OID_HR_STORAGE_DESCR = "1.3.6.1.2.1.25.2.3.1.3"
OID_HR_STORAGE_SIZE = "1.3.6.1.2.1.25.2.3.1.5"
OID_HR_STORAGE_USED = "1.3.6.1.2.1.25.2.3.1.6"
OID_ENT_PHYSICAL_DESCR = "1.3.6.1.2.1.47.1.1.1.1.7"
OID_ENT_PHYSICAL_SERIAL = "1.3.6.1.2.1.47.1.1.1.1.11"

VENDOR_PREFIXES = {
    "1.3.6.1.4.1.9.": "Cisco",
    "1.3.6.1.4.1.11.": "HP/Aruba",
    "1.3.6.1.4.1.24272.": "Ubiquiti",
    "1.3.6.1.4.1.14988.": "MikroTik",
    "1.3.6.1.4.1.2011.": "Huawei",
}


def _hlapi():
    from pysnmp.hlapi import asyncio as hlapi

    get_cmd = getattr(hlapi, "get_cmd", None) or getattr(hlapi, "getCmd")
    next_cmd = getattr(hlapi, "next_cmd", None) or getattr(hlapi, "nextCmd")
    return hlapi, get_cmd, next_cmd


async def _get_async(host, community, oid, port, timeout, retries):
    hlapi, get_cmd, _ = _hlapi()
    async for error, _index, varbinds in get_cmd(
        hlapi.SnmpEngine(),
        hlapi.CommunityData(community, mpModel=1),
        hlapi.UdpTransportTarget((host, port), timeout=timeout, retries=retries),
        hlapi.ContextData(),
        hlapi.ObjectType(hlapi.ObjectIdentity(oid)),
    ):
        if error or not varbinds:
            return None
        return varbinds[0][1].prettyPrint()
    return None


async def _walk_async(host, community, oid, port, timeout, retries):
    hlapi, _, next_cmd = _hlapi()
    result = {}
    async for error, _index, varbinds in next_cmd(
        hlapi.SnmpEngine(),
        hlapi.CommunityData(community, mpModel=1),
        hlapi.UdpTransportTarget((host, port), timeout=timeout, retries=retries),
        hlapi.ContextData(),
        hlapi.ObjectType(hlapi.ObjectIdentity(oid)),
        lexicographicMode=False,
    ):
        if error:
            break
        for varbind in varbinds:
            result[str(varbind[0])] = varbind[1].prettyPrint()
    return result


def snmp_get(host: str, community: str, oid: str, port: int = None, timeout: int = None, retries: int = None) -> str | None:
    port = port or settings.snmp_port
    timeout = timeout or settings.snmp_timeout
    retries = retries if retries is not None else settings.snmp_retries
    try:
        return asyncio.run(_get_async(host, community, oid, port, timeout, retries))
    except Exception:
        return None


def snmp_walk(host: str, community: str, oid: str, port: int = None, timeout: int = None, retries: int = None) -> dict:
    port = port or settings.snmp_port
    timeout = timeout or settings.snmp_timeout
    retries = retries if retries is not None else settings.snmp_retries
    try:
        return asyncio.run(_walk_async(host, community, oid, port, timeout, retries))
    except Exception:
        return {}


def vendor_from_sysobjectid(sysobjectid: str | None) -> str | None:
    if not sysobjectid:
        return None
    for prefix, vendor in VENDOR_PREFIXES.items():
        if sysobjectid.startswith(prefix):
            return vendor
    return None


def classify(sysdescr: str | None, sysobjectid: str | None) -> str:
    text = (sysdescr or "").lower()
    if "router" in text or "isr" in text:
        return "router"
    if "access point" in text or ("wireless" in text and "ap" in text):
        return "access_point"
    if "repeater" in text or "extender" in text:
        return "repeater"
    if "modem" in text or "dsl" in text or "cable" in text or " ont" in text or " onu" in text:
        return "modem"
    if "switch" in text:
        return "switch"
    return "other"


def poll(host: str, community: str, port: int = None, timeout: int = None, retries: int = None) -> dict:
    port = port or settings.snmp_port
    timeout = timeout or settings.snmp_timeout
    retries = retries if retries is not None else settings.snmp_retries
    sysdescr = snmp_get(host, community, OID_SYS_DESCR, port, timeout, retries)
    data = {
        "sysDescr": sysdescr,
        "sysObjectID": snmp_get(host, community, OID_SYS_OBJECT_ID, port, timeout, retries),
        "sysUpTime": snmp_get(host, community, OID_SYS_UPTIME, port, timeout, retries),
        "sysName": snmp_get(host, community, OID_SYS_NAME, port, timeout, retries),
        "ifNumber": snmp_get(host, community, OID_IF_NUMBER, port, timeout, retries),
    }
    if sysdescr is None:
        data["reachable"] = "no"
        return data
    data["reachable"] = "yes"
    data["vendor"] = vendor_from_sysobjectid(data["sysObjectID"])
    data["guessed_type"] = classify(sysdescr, data["sysObjectID"])

    if_descr = snmp_walk(host, community, OID_IF_DESCR, port, timeout, retries)
    if_status = snmp_walk(host, community, OID_IF_OPER_STATUS, port, timeout, retries)
    interfaces = []
    for oid, descr in if_descr.items():
        if_index = oid.rsplit(".", 1)[-1]
        interfaces.append(
            {
                "index": if_index,
                "descr": descr,
                "operStatus": if_status.get(f"{OID_IF_OPER_STATUS}.{if_index}", "unknown"),
            }
        )
    data["interfaces"] = interfaces
    data["interfaces_up"] = sum(1 for item in interfaces if item["operStatus"] in ("1", "up"))

    loads = [
        int(value)
        for value in snmp_walk(host, community, OID_HR_PROCESSOR_LOAD, port, timeout, retries).values()
        if value.isdigit()
    ]
    if loads:
        data["cpu_load_pct"] = str(round(sum(loads) / len(loads)))

    storage_descr = snmp_walk(host, community, OID_HR_STORAGE_DESCR, port, timeout, retries)
    storage_size = snmp_walk(host, community, OID_HR_STORAGE_SIZE, port, timeout, retries)
    storage_used = snmp_walk(host, community, OID_HR_STORAGE_USED, port, timeout, retries)
    for oid, descr in storage_descr.items():
        if "memory" in descr.lower() or "ram" in descr.lower():
            index = oid.rsplit(".", 1)[-1]
            size = storage_size.get(f"{OID_HR_STORAGE_SIZE}.{index}")
            used = storage_used.get(f"{OID_HR_STORAGE_USED}.{index}")
            if size and used and size.isdigit() and int(size) > 0:
                data["mem_used_pct"] = str(round(int(used) * 100 / int(size)))
            break

    descr_map = snmp_walk(host, community, OID_ENT_PHYSICAL_DESCR, port, timeout, retries)
    serial_map = snmp_walk(host, community, OID_ENT_PHYSICAL_SERIAL, port, timeout, retries)
    if descr_map:
        first_key = sorted(descr_map.keys())[0]
        index = first_key.rsplit(".", 1)[-1]
        data["model"] = descr_map[first_key]
        data["serial"] = serial_map.get(f"{OID_ENT_PHYSICAL_SERIAL}.{index}")
    return data
