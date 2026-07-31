---
name: ec2
description: >
  Usa la librería ruvic_ec2_connector para consultar y controlar
  instancias AWS EC2 - listar instancias (list_instances), iniciar una
  instancia detenida (start_instance), detener una instancia en
  ejecución (stop_instance), y consultar el estado actual de una
  instancia (get_instance_state). Úsala cuando el usuario pida
  revisar, prender o apagar servidores EC2.
triggers:
- ec2
- aws ec2
- instancia
- servidor virtual
- maquina virtual aws
---

# Conector AWS EC2 (ruvic_ec2_connector)

Librería Python de consulta y control de instancias EC2. Está
**preinstalada en el runtime** cuando el conector está configurado (si
no, instálala con `pip install git+https://github.com/Dgirto/AWS-EC2.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de
variables de entorno, disponibles cuando el conector `ec2` está
configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_EC2_ACCESS_KEY_ID` | Access Key ID de AWS |
| `RUVIC_EC2_SECRET_ACCESS_KEY` | Secret Access Key de AWS |
| `RUVIC_EC2_REGION` | Región de AWS |
| `RUVIC_EC2_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no
generes código que lo use; indica al usuario que lo configure en
**Settings → Conectores**.

## Este conector combina lectura y escritura

`list_instances` y `get_instance_state` son de solo lectura.
`start_instance` y `stop_instance` **SÍ modifican** el estado real de
una instancia, afectando servicios en producción si se usa sobre la
instancia equivocada. Confirma con el usuario antes de iniciar o
detener una instancia si la acción no fue explícitamente solicitada.

## Conexión (siempre igual)

```python
from ruvic_ec2_connector import Ec2Client

client = Ec2Client()  # lee RUVIC_EC2_* del entorno automáticamente
```

## Capacidad 1 — Listar instancias

```python
instancias = client.list_instances()
for i in instancias:
    print(i["instance_id"], i["state"], i.get("name"))
```

## Capacidad 2 — Iniciar una instancia

```python
client.start_instance("i-0abcd1234")
```

## Capacidad 3 — Detener una instancia

```python
client.stop_instance("i-0abcd1234")
```

## Capacidad 4 — Consultar el estado de una instancia

```python
estado = client.get_instance_state("i-0abcd1234")
print(estado["state"])
```

## Manejo de errores

```python
from ruvic_ec2_connector import (
    Ec2AuthError, Ec2DataError, Ec2NetworkError,
)

try:
    client.stop_instance("i-0abcd1234")
except Ec2AuthError:
    print("Credenciales inválidas o sin permiso IAM suficiente")
except Ec2NetworkError:
    print("No se pudo alcanzar EC2 — reintenta en unos segundos")
except Ec2DataError as e:
    print(f"Error de datos: {e}")  # ej. la instancia no existe o ya está en ese estado
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_EC2_*` (el constructor de `Ec2Client` ya lo hace).
2. Nunca imprimas `RUVIC_EC2_SECRET_ACCESS_KEY` en logs ni en la salida.
3. `start_instance`/`stop_instance` afectan infraestructura real: no las llames sin que el usuario lo haya pedido explícitamente, y confirmá el `instance_id` correcto antes de actuar (usá `list_instances` primero si hay ambigüedad).
4. Antes de detener una instancia, si el contexto no es inequívoco, verificá con el usuario a qué instancia se refiere — parar la equivocada puede afectar un servicio productivo.
5. `stop_instance` NO termina/elimina la instancia — los datos persistentes se conservan y puede volver a iniciarse con `start_instance`.
