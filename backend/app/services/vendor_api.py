import httpx


class VendorRestClient:
    def __init__(self, base_url: str, secret: dict, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self._client = httpx.Client(base_url=self.base_url, verify=False, timeout=timeout)
        self._authenticated = False

    def login(self) -> None:
        api_key = self.secret.get("api_key")
        if api_key:
            self._client.headers["Authorization"] = f"Bearer {api_key}"
            self._authenticated = True
            return
        username = self.secret.get("username")
        password = self.secret.get("password")
        for path in ("/api/auth/login", "/api/login"):
            try:
                response = self._client.post(path, json={"username": username, "password": password})
            except httpx.HTTPError:
                continue
            if response.status_code == 200:
                data = response.json()
                token = data.get("token") or data.get("access_token")
                if not token and isinstance(data.get("data"), dict):
                    token = data["data"].get("token")
                if token:
                    self._client.headers["Authorization"] = f"Bearer {token}"
                    self._authenticated = True
                    return
        raise RuntimeError("Vendor REST login failed")

    def _ensure_auth(self) -> None:
        if not self._authenticated:
            self.login()

    def get(self, path: str) -> dict:
        self._ensure_auth()
        response = self._client.get(path)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, payload: dict) -> dict:
        self._ensure_auth()
        response = self._client.post(path, json=payload)
        response.raise_for_status()
        return response.json()

    def list_devices(self) -> list:
        for path in ("/api/s/default/stat/device", "/api/devices", "/api/v1/devices"):
            try:
                data = self.get(path)
                if isinstance(data, dict) and isinstance(data.get("data"), list):
                    return data["data"]
                if isinstance(data, list):
                    return data
            except httpx.HTTPError:
                continue
        raise RuntimeError("Could not list devices on vendor API")

    def set_wlan(self, ssid: str, passphrase: str | None = None, enabled: bool = True) -> dict:
        payload = {"name": ssid, "enabled": enabled, "security": "wpapsk", "wpa_psk": passphrase or ""}
        for path in ("/api/s/default/rest/wlanconf", "/api/wlan", "/api/v1/wlan"):
            try:
                return self.post(path, payload)
            except httpx.HTTPError:
                continue
        raise RuntimeError("Could not push WLAN config via vendor API")

    def reboot_device(self, mac: str) -> dict:
        for path in ("/api/s/default/cmd/devmgr", "/api/devices/reboot", "/api/v1/devices/reboot"):
            try:
                return self.post(path, {"cmd": "restart", "mac": mac})
            except httpx.HTTPError:
                continue
        raise RuntimeError("Could not reboot device via vendor API")

    def close(self) -> None:
        self._client.close()
