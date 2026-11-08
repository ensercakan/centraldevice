import uuid

import httpx

SOAP_ENVELOPE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
    'xmlns:cwmp="urn:dslforum-org:cwmp-1-2">'
    "<soap:Header><cwmp:ID soap:mustUnderstand=\"1\">{msg_id}</cwmp:ID></soap:Header>"
    "<soap:Body>{body}</soap:Body></soap:Envelope>"
)


def _auth(secret: dict):
    username = secret.get("username")
    password = secret.get("password")
    if username and password:
        return (username, password)
    return None


def _call(acs_url: str, action: str, body: str, secret: dict, timeout: int = 20) -> str:
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"urn:dslforum-org:cwmp-1-2:{action}"',
    }
    content = SOAP_ENVELOPE.format(msg_id=str(uuid.uuid4()), body=body)
    with httpx.Client(verify=False, timeout=timeout, auth=_auth(secret)) as client:
        response = client.post(acs_url, content=content, headers=headers)
        response.raise_for_status()
        return response.text


def get_parameter_values(acs_url: str, secret: dict, parameters: list[str]) -> str:
    items = "".join(f"<string>{p}</string>" for p in parameters)
    body = f"<cwmp:GetParameterValues><ParameterNames>{items}</ParameterNames></cwmp:GetParameterValues>"
    return _call(acs_url, "GetParameterValues", body, secret)


def set_parameter_values(acs_url: str, secret: dict, values: dict[str, str], commit: bool = True) -> str:
    items = "".join(
        f'<ParameterValueStruct><ParameterName>{name}</ParameterName>'
        f'<ParameterValue xsi:type="cwmp:string" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">{value}</ParameterValue>'
        "</ParameterValueStruct>"
        for name, value in values.items()
    )
    body = (
        f"<cwmp:SetParameterValues><ParameterList>{items}</ParameterList>"
        f"<ParameterKey>centraldevice-{uuid.uuid4()}</ParameterKey></cwmp:SetParameterValues>"
    )
    response = _call(acs_url, "SetParameterValues", body, secret)
    if commit:
        _call(acs_url, "SetParameterValuesCommit", "<cwmp:Commit/>", secret)
    return response


def reboot(acs_url: str, secret: dict) -> str:
    return _call(acs_url, "Reboot", "<cwmp:Reboot><CommandKey>centraldevice-reboot</CommandKey></cwmp:Reboot>", secret)


def download_firmware(acs_url: str, secret: dict, firmware_url: str, file_type: str = "1 Firmware Upgrade Image") -> str:
    body = (
        "<cwmp:Download><CommandKey>centraldevice-fw</CommandKey>"
        f"<FileType>{file_type}</FileType><URL>{firmware_url}</URL>"
        "<Username></Username><Password></Password>"
        "<FileSize>0</FileSize><TargetFileName></TargetFileName>"
        "<DelaySeconds>0</DelaySeconds><SuccessURL></SuccessURL><FailureURL></FailureURL>"
        "</cwmp:Download>"
    )
    return _call(acs_url, "Download", body, secret)
