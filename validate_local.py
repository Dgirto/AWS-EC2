"""Validación local del conector ec2: ejercita las 4 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_EC2_* exportadas en el entorno, y el ID de
una instancia de prueba (editá TEST_INSTANCE_ID abajo).

ADVERTENCIA: este script detiene y vuelve a iniciar una instancia EC2
REAL. Ejecútalo solo contra una instancia de prueba dedicada, nunca
contra una instancia productiva.
"""

from ruvic_ec2_connector import Ec2Client, setup_logging

TEST_INSTANCE_ID = "i-0000000000000000"  # <-- reemplaza por una instancia de prueba real

setup_logging("INFO")
client = Ec2Client()

print("== 1. Listar instancias ==")
instancias = client.list_instances()
for i in instancias[:5]:
    print(f"  {i['instance_id']}: {i['state']} ({i.get('name')})")

print("== 2. Consultar estado de la instancia de prueba ==")
estado = client.get_instance_state(TEST_INSTANCE_ID)
print(f"  {estado}")

print("== 3. Detener instancia de prueba ==")
nuevo_estado = client.stop_instance(TEST_INSTANCE_ID)
print(f"  nuevo estado: {nuevo_estado}")

print("== 4. Iniciar instancia de prueba ==")
nuevo_estado = client.start_instance(TEST_INSTANCE_ID)
print(f"  nuevo estado: {nuevo_estado}")

print("\nTodo OK: list_instances, get_instance_state, stop_instance y start_instance funcionan.")
