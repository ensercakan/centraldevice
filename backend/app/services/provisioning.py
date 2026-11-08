from app.models import AccessMethod, Credential, Device
from app.services import ssh_service, tr069_service, vendor_api

TR069_PARAM_MAP = {
    "ssid": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID",
    "wifi_passphrase": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.KeyPassphrase",
    "wifi_enabled": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.Enable",
    "wan_username": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username",
    "wan_password": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Password",
    "hostname": "InternetGatewayDevice.DeviceInfo.HostName",
}


def render_commands(template: str, variables: dict) -> list[str]:
    commands = []
    for line in template.splitlines():
        if not line.strip():
            continue
        try:
            commands.append(line.format(**variables))
        except (KeyError, IndexError):
            commands.append(line)
    return commands


def pick_credential(device: Device, method: AccessMethod | None, db) -> Credential:
    query = db.query(Credential).filter(
        (Credential.device_id == device.id) | (Credential.device_id.is_(None))
    )
    if method is not None:
        query = query.filter(Credential.access_method == method)
    cred = query.order_by(Credential.device_id.is_(None)).first()
    if cred is None:
        raise RuntimeError(f"No stored credential for device {device.ip_address} (method={method})")
    return cred


def apply_config(device: Device, cred: Credential, payload: dict) -> dict:
    from app.security import decrypt_secret

    secret = decrypt_secret(cred.encrypted_secret)
    method = cred.access_method
    variables = payload.get("variables", {})
    template = payload.get("template", "")

    if method == AccessMethod.ssh:
        commands = render_commands(template, variables)
        if not commands:
            raise RuntimeError("Empty config template")
        output = ssh_service.push_config(device.ip_address, secret, commands)
        return {"method": "ssh", "commands": commands, "output": output[-4000:]}

    if method == AccessMethod.rest:
        base_url = device.management_url or variables.get("base_url")
        if not base_url:
            raise RuntimeError("management_url or base_url variable required for REST devices")
        client = vendor_api.VendorRestClient(base_url, secret)
        try:
            client.login()
            if "ssid" in variables:
                result = client.set_wlan(
                    variables["ssid"],
                    variables.get("wifi_passphrase"),
                    bool(variables.get("wifi_enabled", True)),
                )
                return {"method": "rest", "result": result}
            if template:
                commands = render_commands(template, variables)
                return {"method": "rest", "commands": commands, "note": "raw template requires vendor-specific endpoint"}
            raise RuntimeError("REST config push requires 'ssid' variable or a template")
        finally:
            client.close()

    if method == AccessMethod.tr069:
        acs_url = device.management_url or variables.get("acs_url")
        if not acs_url:
            raise RuntimeError("management_url (ACS URL) required for TR-069 devices")
        values = {}
        for key, value in variables.items():
            param = TR069_PARAM_MAP.get(key, key if "." in key else None)
            if param is None:
                continue
            values[param] = str(value)
        if not values:
            raise RuntimeError("No mappable TR-069 parameters in variables")
        response = tr069_service.set_parameter_values(acs_url, secret, values)
        return {"method": "tr069", "parameters": values, "response": response[-4000:]}

    raise RuntimeError(f"Config push not supported over {method.value}")


def reboot_device(device: Device, cred: Credential) -> dict:
    from app.security import decrypt_secret

    secret = decrypt_secret(cred.encrypted_secret)
    if cred.access_method == AccessMethod.tr069:
        acs_url = device.management_url
        if not acs_url:
            raise RuntimeError("management_url (ACS URL) required for TR-069 devices")
        return {"method": "tr069", "response": tr069_service.reboot(acs_url, secret)[-2000:]}
    if cred.access_method == AccessMethod.rest:
        client = vendor_api.VendorRestClient(device.management_url, secret)
        try:
            client.login()
            return {"method": "rest", "result": client.reboot_device(device.mac or device.ip_address)}
        finally:
            client.close()
    if cred.access_method == AccessMethod.ssh:
        return {"method": "ssh", "output": ssh_service.reboot(device.ip_address, secret)[-2000:]}
    raise RuntimeError("Reboot not supported over SNMP")


def push_firmware(device: Device, cred: Credential, firmware_url: str) -> dict:
    from app.security import decrypt_secret

    secret = decrypt_secret(cred.encrypted_secret)
    if cred.access_method == AccessMethod.tr069:
        if not device.management_url:
            raise RuntimeError("management_url (ACS URL) required for TR-069 firmware push")
        return {"method": "tr069", "response": tr069_service.download_firmware(device.management_url, secret, firmware_url)[-2000:]}
    raise RuntimeError(f"Firmware push over {cred.access_method.value} is not supported; use TR-069 Download RPC")
