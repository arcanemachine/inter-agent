from __future__ import annotations

import ipaddress
import os
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class TlsConfigError(RuntimeError):
    """Raised when TLS configuration cannot be used."""


DEFAULT_CERT_NAME = "tls-cert.pem"
DEFAULT_KEY_NAME = "tls-key.pem"


def default_cert_path(data_dir: Path) -> Path:
    return data_dir / DEFAULT_CERT_NAME


def default_key_path(data_dir: Path) -> Path:
    return data_dir / DEFAULT_KEY_NAME


def resolved_tls_paths(
    data_dir: Path,
    cert_path: Path | None = None,
    key_path: Path | None = None,
) -> tuple[Path, Path]:
    if (cert_path is None) != (key_path is None):
        raise TlsConfigError("TLS requires both certificate and key paths, or neither")
    if cert_path is not None and key_path is not None:
        return cert_path, key_path
    return default_cert_path(data_dir), default_key_path(data_dir)


def ensure_tls_material(
    data_dir: Path,
    host: str,
    cert_path: Path | None = None,
    key_path: Path | None = None,
) -> tuple[Path, Path]:
    cert, key = resolved_tls_paths(data_dir, cert_path, key_path)
    if cert.exists() and key.exists():
        os.chmod(cert, 0o600)
        os.chmod(key, 0o600)
        return cert, key
    if cert_path is not None or key_path is not None:
        raise TlsConfigError(f"configured TLS certificate or key does not exist: {cert}, {key}")
    data_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(data_dir, 0o700)
    _generate_self_signed_cert(cert, key, host)
    return cert, key


def build_server_ssl_context(
    data_dir: Path,
    host: str,
    cert_path: Path | None = None,
    key_path: Path | None = None,
) -> ssl.SSLContext:
    cert, key = ensure_tls_material(data_dir, host, cert_path, key_path)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(certfile=cert, keyfile=key)
    except OSError as exc:
        raise TlsConfigError(f"could not load TLS certificate or key: {exc}") from exc
    return context


def build_client_ssl_context(
    data_dir: Path,
    cert_path: Path | None = None,
) -> ssl.SSLContext:
    cert = cert_path or default_cert_path(data_dir)
    if not cert.exists():
        raise TlsConfigError(
            f"TLS certificate not found at {cert}; "
            "start the server or configure INTER_AGENT_TLS_CERT"
        )
    context = ssl.create_default_context(cafile=str(cert))
    context.check_hostname = False
    return context


def _subject_alt_names(host: str) -> list[x509.GeneralName]:
    names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ipaddress.ip_address("::1")),
    ]
    try:
        names.append(x509.IPAddress(ipaddress.ip_address(host)))
    except ValueError:
        if host:
            names.append(x509.DNSName(host))
    return names


def _generate_self_signed_cert(cert_path: Path, key_path: Path, host: str) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "inter-agent local TLS"),
        ]
    )
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(_subject_alt_names(host)), critical=False)
        .sign(private_key, hashes.SHA256())
    )

    cert_temp = cert_path.with_name(f".{cert_path.name}.{os.getpid()}.tmp")
    key_temp = key_path.with_name(f".{key_path.name}.{os.getpid()}.tmp")
    cert_temp.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_temp.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(cert_temp, 0o600)
    os.chmod(key_temp, 0o600)
    os.replace(cert_temp, cert_path)
    os.replace(key_temp, key_path)
    os.chmod(cert_path, 0o600)
    os.chmod(key_path, 0o600)
