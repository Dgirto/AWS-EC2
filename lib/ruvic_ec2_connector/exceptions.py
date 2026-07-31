"""Excepciones propias del conector EC2.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del SDK subyacente.
"""


class Ec2ConnectorError(Exception):
    """Error base del conector."""


class Ec2AuthError(Ec2ConnectorError):
    """Credenciales inválidas o permisos IAM insuficientes."""


class Ec2NetworkError(Ec2ConnectorError):
    """No se pudo alcanzar el servicio EC2 (red/timeout)."""


class Ec2DataError(Ec2ConnectorError):
    """La operación es válida pero la instancia/parámetro es inválido."""
