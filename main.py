import os
import time
import grpc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'data')

from protos import replication_pb2, replication_pb2_grpc
from src.core_node import CoreNode
from src.layer1_node import Layer1Node
from src.layer2_node import Layer2Node
from web import flask_server

def execute_transaction(transaccio, nodes):
    transaccio = transaccio.strip()
    if not transaccio:
        return

    print("Transacció actual: ", transaccio)

    operacions = [op.strip() for op in transaccio.split(', ')]

    layer = 0
    target_nodes = []

    begin_op = operacions[0]
    if begin_op.startswith('b'):
        if len(begin_op) > 1 and begin_op[1].isdigit():
            layer = int(begin_op[1])

        if layer == 0:
            target_nodes = [nodes['A1'], nodes['A2'], nodes['A3']]
        elif layer == 1:
            target_nodes = [nodes['B1'], nodes['B2']]
        elif layer == 2:
            target_nodes = [nodes['C1'], nodes['C2']]

    if not target_nodes:
        print("Error: No target nodes found")
        return

    target_node = target_nodes[0]
    port = target_node['port']

    for op in operacions[1:-1]:
        op = op.strip()

        if op.startswith('r('):
            key = int(op[2:-1])
            try:
                with grpc.insecure_channel(f'localhost:{port}') as channel:
                    stub = replication_pb2_grpc.ReplicationServiceStub(channel)
                    request = replication_pb2.ReadRequest(key=key, node_id=target_node['id'])
                    response = stub.Read(request, timeout=5)
                    if response.success:
                        print(f"  READ({key}) = {response.value} from {target_node['id']}")
                    else:
                        print(f"  READ({key}) FAILED: {response.message}")
            except Exception as e:
                print(f"  Error reading from {target_node['id']}: {e}")

        elif op.startswith('w('):
            parts = op[2:-1].split(',')
            key = int(parts[0])
            value = int(parts[1])
            try:
                with grpc.insecure_channel(f'localhost:{port}') as channel:
                    stub = replication_pb2_grpc.ReplicationServiceStub(channel)
                    request = replication_pb2.WriteRequest(key=key, value=value, node_id=target_node['id'])
                    response = stub.Write(request, timeout=5)
                    if response.success:
                        print(f"  WRITE({key}, {value}) SUCCESS on {target_node['id']}")
                    else:
                        print(f"  WRITE FAILED: {response.message}")
            except Exception as e:
                print(f"  Error writing to {target_node['id']}: {e}")

    print(f"Transaction completed\n")
    time.sleep(1)


def main():
    print("Iniciant sistema...")

    flask_server.start()
    time.sleep(2)

    print("Dashboard: http://localhost:8080")

    ports = {
        'A1': 9090,
        'A2': 9091,
        'A3': 9092,
        'B1': 9093,
        'B2': 9094,
        'C1': 9095,
        'C2': 9096
    }

    print("=== Creant Core Layer ===")
    node_A1 = CoreNode('A1', ports['A1'], peer_ports=[ports['A2'], ports['A3']], layer1_ports=[], data_dir=LOGS_DIR)
    node_A2 = CoreNode('A2', ports['A2'], peer_ports=[ports['A1'], ports['A3']], layer1_ports=[ports['B1']], data_dir=LOGS_DIR)
    node_A3 = CoreNode('A3', ports['A3'], peer_ports=[ports['A1'], ports['A2']], layer1_ports=[ports['B2']], data_dir=LOGS_DIR)
    node_A1.start()
    node_A2.start()
    node_A3.start()
    time.sleep(1)

    print("\n=== Creant Layer 1 ===")
    node_B1 = Layer1Node('B1', ports['B1'], layer2_ports=[], data_dir=LOGS_DIR)
    node_B2 = Layer1Node('B2', ports['B2'], layer2_ports=[ports['C1'], ports['C2']], data_dir=LOGS_DIR)
    node_B1.start()
    node_B2.start()
    time.sleep(1)

    print("\n=== Creant Layer 2 ===")
    node_C1 = Layer2Node('C1', ports['C1'], data_dir=LOGS_DIR)
    node_C2 = Layer2Node('C2', ports['C2'], data_dir=LOGS_DIR)
    node_C1.start()
    node_C2.start()
    time.sleep(1)

    print("Nodes creats")

    nodes = {
        'A1': {'port': ports['A1'], 'id': 'A1', 'node': node_A1},
        'A2': {'port': ports['A2'], 'id': 'A2', 'node': node_A2},
        'A3': {'port': ports['A3'], 'id': 'A3', 'node': node_A3},
        'B1': {'port': ports['B1'], 'id': 'B1', 'node': node_B1},
        'B2': {'port': ports['B2'], 'id': 'B2', 'node': node_B2},
        'C1': {'port': ports['C1'], 'id': 'C1', 'node': node_C1},
        'C2': {'port': ports['C2'], 'id': 'C2', 'node': node_C2}
    }

    print("Execució de transaccions\n")
    time.sleep(2)

    transactions_file = os.path.join(LOGS_DIR, 'transactions.txt')

    try:
        with open(transactions_file, 'r') as f:
            transactions = f.readlines()

        for transaction in transactions:
            if transaction.strip():
                execute_transaction(transaction, nodes)
                time.sleep(1.5)

    except FileNotFoundError:
        print("No s'ha trobat data/transactions.txt")
    except Exception as e:
        print("Error al executar transaccions")

    print("Transaccions finalitzades")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node_A1.stop()
        node_A2.stop()
        node_A3.stop()
        node_B1.stop()
        node_B2.stop()
        node_C1.stop()
        node_C2.stop()
        flask_server.stop()
        print("Aturant...")


if __name__ == '__main__':
    main()
