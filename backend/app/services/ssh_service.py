def _connection_params(host: str, secret: dict) -> dict:
    return {
        "device_type": secret.get("device_type", "autodetect"),
        "host": host,
        "port": int(secret.get("port", 22)),
        "username": secret.get("username", ""),
        "password": secret.get("password", ""),
        "secret": secret.get("enable_password", ""),
        "timeout": int(secret.get("timeout", 10)),
        "session_timeout": int(secret.get("session_timeout", 30)),
    }


def run_show_commands(host: str, secret: dict, commands: list[str]) -> dict:
    from netmiko import ConnectHandler

    conn = ConnectHandler(**_connection_params(host, secret))
    try:
        return {cmd: conn.send_command(cmd) for cmd in commands}
    finally:
        conn.disconnect()


def push_config(host: str, secret: dict, commands: list[str], save: bool = True) -> str:
    from netmiko import ConnectHandler

    conn = ConnectHandler(**_connection_params(host, secret))
    try:
        output = conn.send_config_set(commands)
        if save:
            try:
                output += "\n" + conn.save_config()
            except Exception:
                pass
        return output
    finally:
        conn.disconnect()


def reboot(host: str, secret: dict, reload_command: str = "reload") -> str:
    from netmiko import ConnectHandler

    conn = ConnectHandler(**_connection_params(host, secret))
    try:
        return conn.send_command(reload_command, expect_string=r"[confirm]", strip_command=False)
    finally:
        conn.disconnect()
