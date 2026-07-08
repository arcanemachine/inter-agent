from __future__ import annotations

import ipaddress
import ssl
from pathlib import Path

from inter_agent.core.config import EndpointResolution
from inter_agent.core.tls import build_client_ssl_context


def websocket_uri(host: str, port: int, tls: bool = False) -> str:
    scheme = "wss" if tls else "ws"
    try:
        display_host = f"[{host}]" if ipaddress.ip_address(host).version == 6 else host
    except ValueError:
        display_host = host
    return f"{scheme}://{display_host}:{port}"


def client_ssl_context(
    tls: bool,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> ssl.SSLContext | None:
    if not tls:
        return None
    if data_dir is None:
        raise ValueError("TLS client connections require a data directory")
    return build_client_ssl_context(data_dir, tls_cert_path)


def endpoint_uri(endpoint: EndpointResolution) -> str:
    return websocket_uri(endpoint.host, endpoint.port, endpoint.tls)


def endpoint_ssl_context(endpoint: EndpointResolution) -> ssl.SSLContext | None:
    return client_ssl_context(endpoint.tls, endpoint.data_dir, endpoint.tls_cert_path)
