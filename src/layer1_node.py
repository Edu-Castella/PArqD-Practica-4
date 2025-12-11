import grpc
from concurrent import futures
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protos import replication_pb2, replication_pb2_grpc

try:
    from web import flask_server
except ImportError:
    flask_server = None


class Layer1Node(replication_pb2_grpc.ReplicationServiceServicer):
    def __init__(self, node_id, port, layer2_ports, data_dir):
        self.node_id = node_id
        self.port = port
        self.layer2_ports = layer2_ports
        self.data = {}
        self.version = 0
        self.log_file = os.path.join(data_dir, f"{node_id}_log.txt")
        self.server = None
        self.propagation_timer = None

        with open(self.log_file, 'w') as f:
            f.write(f"LOG NODE {node_id}\n")
            f.write(f"Versio 0: BUIT\n")

        self.PropagacioTimer()

    def Read(self, request, context):
        key = request.key
        if key in self.data:
            value = self.data[key]
            return replication_pb2.ReadResponse(value=value, success=True, message="OK")
        else:
            return replication_pb2.ReadResponse(value=0, success=False, message="Key not found")

    def PropagateUpdate(self, request, context):
        for key, value in request.data.items():
            self.data[key] = value

        self.version = request.version

        self.WriteLog()

        return replication_pb2.PropagateResponse(success=True)

    def PropagacioTimer(self):

        def _PropagacioTimer():
            while True:
                time.sleep(10)
                if self.data:
                    self.PropagarLayer2()
        self.propagation_timer = threading.Thread(target=_PropagacioTimer, daemon=True)
        self.propagation_timer.start()

    def PropagarLayer2(self):
        if not self.layer2_ports:
            return

        for layer2_port in self.layer2_ports:
            try:
                with grpc.insecure_channel(f'localhost:{layer2_port}') as channel:
                    stub = replication_pb2_grpc.ReplicationServiceStub(channel)
                    request = replication_pb2.PropagateRequest(
                        data=self.data,
                        version=self.version
                    )
                    response = stub.PropagateUpdate(request, timeout=2)
            except Exception as e:
                pass

    def start(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        replication_pb2_grpc.add_ReplicationServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(f'[::]:{self.port}')
        self.server.start()

    def stop(self):
        if self.server:
            self.server.stop(0)

    def WriteLog(self):
        with open(self.log_file, 'a') as f:
            f.write(f"\nVersio {self.version}\n")
            if not self.data:
                f.write("(Buit)\n")
            else:
                for key in sorted(self.data.keys()):
                    f.write(f"key={key}, value={self.data[key]}\n")

        self.EnviarWeb()

    def EnviarWeb(self):
        if flask_server:
            data = {
                'type': 'node_update',
                'layer': 'layer1',
                'node_id': self.node_id,
                'version': self.version,
                'data': {str(k): v for k, v in self.data.items()},
                'data_count': len(self.data)
            }
            flask_server.broadcast(data)