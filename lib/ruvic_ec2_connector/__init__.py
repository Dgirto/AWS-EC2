"""Conector Ruvic de consulta y control de instancias AWS EC2."""

from .client import Ec2Client
from .config import ENV_PREFIX, Ec2Config
from .exceptions import Ec2AuthError, Ec2ConnectorError, Ec2DataError, Ec2NetworkError
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "Ec2AuthError",
    "Ec2Client",
    "Ec2Config",
    "Ec2ConnectorError",
    "Ec2DataError",
    "Ec2NetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
