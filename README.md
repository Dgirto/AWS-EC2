# Conector AWS EC2 (CON-068)

Conector Ruvic de consulta y control de instancias AWS EC2. Permite
listar instancias, iniciar/detener una instancia, y consultar su
estado actual.

## Instalación

```bash
pip install git+https://github.com/Dgirto/AWS-EC2.git#subdirectory=lib
```

Python 3.10+. Dependencia única: `boto3>=1.34,<2.0`.

## Permisos requeridos en AWS (IAM)

Crea un usuario o rol IAM con una policy limitada al alcance necesario:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:StartInstances",
        "ec2:StopInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/RuvicManaged": "true"
        }
      }
    }
  ]
}
```

Se recomienda restringir `StartInstances`/`StopInstances` con una
condición de tag (como en el ejemplo) para que el conector solo pueda
controlar instancias explícitamente marcadas, no todas las instancias
de la cuenta. No se otorgan permisos de administración
(`ec2:RunInstances`, `ec2:TerminateInstances`, cambios de red o grupos
de seguridad).

## Variables de entorno (`RUVIC_EC2_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_EC2_ACCESS_KEY_ID` | Sí | Access Key ID de AWS |
| `RUVIC_EC2_SECRET_ACCESS_KEY` | Sí | Secret Access Key de AWS |
| `RUVIC_EC2_REGION` | Sí | Región de AWS (ej. `us-east-1`) |
| `RUVIC_EC2_CONNECT_TIMEOUT` | No (default `10`) | Timeout de conexión en segundos |

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_EC2_ACCESS_KEY_ID=tu-access-key
export RUVIC_EC2_SECRET_ACCESS_KEY=tu-secret-key
export RUVIC_EC2_REGION=us-east-1

python test_connection.py
```

Antes de correr `validate_local.py`, editá `TEST_INSTANCE_ID` con el ID
de una **instancia de prueba dedicada** — el script la detiene y
vuelve a iniciar realmente. Nunca lo apuntes a una instancia
productiva.

```bash
python validate_local.py
```

Prueba también los casos de error (credenciales inválidas, instancia
inexistente, instancia ya en el estado solicitado) y verifica que los
mensajes sean claros.

## Notas de integración

- `list_instances` y `get_instance_state` son de **solo lectura**.
  `start_instance` y `stop_instance` **SÍ modifican** el estado real de
  una instancia. Confirma con el usuario antes de iniciar o detener una
  instancia si la acción no fue explícitamente solicitada.
- `stop_instance` no es lo mismo que terminar/eliminar la instancia
  (`ec2:TerminateInstances`, que este conector no expone) — los datos
  del disco (si no es una instancia efímera) se conservan.
- El nombre de una instancia (tag `Name`) puede ser `None` si la
  instancia no tiene ese tag configurado.
