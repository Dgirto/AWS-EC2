"""Cliente de consulta y control de instancias para AWS EC2.

Capacidades:
- list_instances():   listar instancias EC2 de la región configurada.
- start_instance():    iniciar una instancia detenida.
- stop_instance():     detener una instancia en ejecución.
- get_instance_state(): consultar el estado actual de una instancia.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_EC2_*
(ver config.Ec2Config.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

from .config import Ec2Config
from .exceptions import Ec2AuthError, Ec2ConnectorError, Ec2DataError, Ec2NetworkError
from .logging_utils import get_logger

_AUTH_ERROR_CODES = {
    "UnauthorizedOperation",
    "AuthFailure",
    "UnrecognizedClientException",
    "InvalidClientTokenId",
    "InvalidSignatureException",
}
_NOT_FOUND_ERROR_CODES = {"InvalidInstanceID.NotFound"}
_MAX_LIST_LIMIT = 200


def _wrap_client_error(exc: ClientError, not_found_message: str) -> Ec2ConnectorError:
    """Traduce un error de la API de AWS a una excepción propia, sin dejar
    escapar nunca el tipo crudo del SDK."""
    code = exc.response.get("Error", {}).get("Code", "")
    if code in _AUTH_ERROR_CODES:
        return Ec2AuthError(
            "Credenciales inválidas o sin permiso IAM suficiente para esta "
            "operación. Revisa la policy adjunta al usuario o rol."
        )
    if code in _NOT_FOUND_ERROR_CODES:
        return Ec2DataError(not_found_message)
    if code == "InvalidParameterValue":
        return Ec2DataError(f"Parámetro inválido: {exc}")
    if code == "IncorrectInstanceState":
        return Ec2DataError(
            "La instancia no está en un estado válido para esta operación "
            f"(ej. ya está detenida/iniciada): {exc}"
        )
    return Ec2DataError(f"Error de datos ({code}): {exc}")


class Ec2Client:
    """Cliente de consulta y control de instancias EC2 en la región
    configurada.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_EC2_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = Ec2Client()  # lee RUVIC_EC2_* del entorno
        >>> client.list_instances()
        [{'instance_id': 'i-0abcd1234', 'state': 'running', ...}]
    """

    def __init__(self, config: Ec2Config | None = None) -> None:
        self.config = config or Ec2Config.from_env()
        self._logger = get_logger()
        self._client: Any = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._client = boto3.client(
            "ec2",
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key,
            region_name=self.config.region,
            config=BotoConfig(
                connect_timeout=self.config.connect_timeout,
                read_timeout=max(self.config.connect_timeout, 30),
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )
        return self._client

    def ping(self) -> bool:
        """Verifica la conexión listando hasta 1 instancia.

        Returns:
            True si la conexión funciona.

        Raises:
            Ec2AuthError / Ec2NetworkError / Ec2DataError.
        """
        self.list_instances(max_results=1)
        self._logger.info("Ping exitoso a EC2 en %s", self.config.region)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: listar instancias
    # ------------------------------------------------------------------ #

    def list_instances(self, max_results: int = 50) -> list[dict[str, Any]]:
        """Lista las instancias EC2 de la región configurada.

        Args:
            max_results: máximo de instancias a retornar (default 50,
                máximo 200).

        Returns:
            Lista de dicts: {"instance_id", "state", "instance_type",
            "name", "private_ip", "public_ip", "launch_time"}.

        Ejemplo:
            >>> client.list_instances()
            [{'instance_id': 'i-0abcd1234', 'state': 'running', ...}]
        """
        max_results = max(5, min(int(max_results), _MAX_LIST_LIMIT))
        client = self._get_client()
        try:
            response = client.describe_instances(MaxResults=max_results)
        except ClientError as exc:
            raise _wrap_client_error(exc, "No se pudieron listar las instancias.") from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise Ec2NetworkError(
                f"No se pudo conectar al servicio EC2 en la región "
                f"{self.config.region!r} (timeout {self.config.connect_timeout}s). "
                "Verifica la región y el acceso de red."
            ) from exc

        result = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                name = next(
                    (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
                    None,
                )
                result.append(
                    {
                        "instance_id": instance["InstanceId"],
                        "state": instance["State"]["Name"],
                        "instance_type": instance.get("InstanceType"),
                        "name": name,
                        "private_ip": instance.get("PrivateIpAddress"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "launch_time": instance["LaunchTime"].isoformat()
                        if instance.get("LaunchTime")
                        else None,
                    }
                )
        self._logger.info("Se listaron %d instancia(s) en %s", len(result), self.config.region)
        return result

    # ------------------------------------------------------------------ #
    # Capacidad 2: iniciar una instancia
    # ------------------------------------------------------------------ #

    def start_instance(self, instance_id: str) -> str:
        """Inicia una instancia EC2 detenida.

        Args:
            instance_id: ID de la instancia (ej. "i-0abcd1234").

        Returns:
            El nuevo estado de la instancia (ej. "pending").

        Ejemplo:
            >>> client.start_instance("i-0abcd1234")
            'pending'
        """
        instance_id = (instance_id or "").strip()
        if not instance_id:
            raise Ec2DataError("instance_id no puede estar vacío.")
        client = self._get_client()
        try:
            response = client.start_instances(InstanceIds=[instance_id])
        except ClientError as exc:
            raise _wrap_client_error(
                exc, f"La instancia {instance_id!r} no existe o no es accesible."
            ) from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise Ec2NetworkError(f"No se pudo iniciar la instancia: {exc}") from exc
        new_state = response["StartingInstances"][0]["CurrentState"]["Name"]
        self._logger.info("Instancia %s iniciada, estado: %s", instance_id, new_state)
        return new_state

    # ------------------------------------------------------------------ #
    # Capacidad 3: detener una instancia
    # ------------------------------------------------------------------ #

    def stop_instance(self, instance_id: str) -> str:
        """Detiene una instancia EC2 en ejecución.

        Args:
            instance_id: ID de la instancia (ej. "i-0abcd1234").

        Returns:
            El nuevo estado de la instancia (ej. "stopping").

        Ejemplo:
            >>> client.stop_instance("i-0abcd1234")
            'stopping'
        """
        instance_id = (instance_id or "").strip()
        if not instance_id:
            raise Ec2DataError("instance_id no puede estar vacío.")
        client = self._get_client()
        try:
            response = client.stop_instances(InstanceIds=[instance_id])
        except ClientError as exc:
            raise _wrap_client_error(
                exc, f"La instancia {instance_id!r} no existe o no es accesible."
            ) from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise Ec2NetworkError(f"No se pudo detener la instancia: {exc}") from exc
        new_state = response["StoppingInstances"][0]["CurrentState"]["Name"]
        self._logger.info("Instancia %s detenida, estado: %s", instance_id, new_state)
        return new_state

    # ------------------------------------------------------------------ #
    # Capacidad 4: consultar el estado de una instancia
    # ------------------------------------------------------------------ #

    def get_instance_state(self, instance_id: str) -> dict[str, Any]:
        """Consulta el estado actual de una instancia.

        Args:
            instance_id: ID de la instancia (ej. "i-0abcd1234").

        Returns:
            Dict con: instance_id, state, state_reason.

        Ejemplo:
            >>> client.get_instance_state("i-0abcd1234")
            {'instance_id': 'i-0abcd1234', 'state': 'running', 'state_reason': None}
        """
        instance_id = (instance_id or "").strip()
        if not instance_id:
            raise Ec2DataError("instance_id no puede estar vacío.")
        client = self._get_client()
        try:
            response = client.describe_instance_status(
                InstanceIds=[instance_id], IncludeAllInstances=True
            )
        except ClientError as exc:
            raise _wrap_client_error(
                exc, f"La instancia {instance_id!r} no existe o no es accesible."
            ) from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise Ec2NetworkError(f"No se pudo consultar el estado: {exc}") from exc

        statuses = response.get("InstanceStatuses", [])
        if not statuses:
            raise Ec2DataError(f"La instancia {instance_id!r} no existe o no es accesible.")
        status = statuses[0]
        return {
            "instance_id": status["InstanceId"],
            "state": status["InstanceState"]["Name"],
            "state_reason": status.get("Events", [{}])[0].get("Description")
            if status.get("Events")
            else None,
        }
