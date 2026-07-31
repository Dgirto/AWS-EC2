"""Prueba de conexión estándar del conector ec2.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_EC2_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Conecta a EC2 y lista una instancia usando las env vars
    RUVIC_EC2_*."""
    try:
        from ruvic_ec2_connector import (
            Ec2AuthError,
            Ec2Client,
            Ec2DataError,
            Ec2NetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-ec2-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "AWS-EC2.git#subdirectory=lib",
        )

    try:
        client = Ec2Client()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except Ec2AuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except Ec2NetworkError as exc:
        return False, f"Error de red: {exc}"
    except Ec2DataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        f"Conexión exitosa a EC2 en la región {client.config.region!r}",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
