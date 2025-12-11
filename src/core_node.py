import grpc
from concurrent import futures
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protos import replication_pb2, replication_pb2_grpc

try:
    from web import flask_server
except ImportError:
    flask_server = None


class CoreNode(replication_pb2_grpc.ReplicationServiceServicer):
    def __init__(self, node_id, port, peer_ports, layer1_ports, data_dir):
        self.node_id = node_id
        self.port = port
        self.peer_ports = peer_ports
        self.layer1_ports = layer1_ports
        self.data = {}
        self.version = 0
        self.update_count = 0
        self.log_file = os.path.join(data_dir, f"{node_id}_log.txt")
        self.server = None

        with open(self.log_file, 'w') as f:
            f.write(f"LOG NODE {node_id}\n")
            f.write(f"Versio 0: BUIT\n")

    def Read(self, request, context):
        key = request.key
        if key in self.data:
            value = self.data[key]
            return replication_pb2.ReadResponse(value=value, success=True, message="OK")
        else:
            return replication_pb2.ReadResponse(value=0, success=False, message="Key not found")

    def Write(self, request, context):
        key = request.key
        value = request.value

        self.data[key] = value
        self.version += 1
        self.update_count += 1

        self.WriteLog()

        self.PropagarCoreNodes()

        if self.update_count % 10 == 0:
            self.PropagarLayer1()

        return replication_pb2.WriteResponse(success=True, message="Write successful")

    def SyncCoreNodes(self, request, context):
        for key, value in request.data.items():
            self.data[key] = value

        if request.version > self.version:
            self.version = request.version
            self.update_count = request.version

        self.WriteLog()

        if self.update_count > 0 and self.update_count % 10 == 0 and self.layer1_ports:
            self.PropagarLayer1()

        return replication_pb2.SyncResponse(success=True)

    def PropagarCoreNodes(self):
        for peer_port in self.peer_ports:
            try:
                with grpc.insecure_channel(f'localhost:{peer_port}') as channel:
                    stub = replication_pb2_grpc.ReplicationServiceStub(channel)
                    request = replication_pb2.SyncRequest(
                        data=self.data,
                        version=self.version,
                        sender_id=self.node_id
                    )
                    stub.SyncCoreNodes(request, timeout=2)
            except Exception as e:
                pass

    def PropagarLayer1(self):
        if not self.layer1_ports:
            return

        for layer1_port in self.layer1_ports:
            try:
                with grpc.insecure_channel(f'localhost:{layer1_port}') as channel:
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
            f.write(f"\n=== Version {self.version} ===\n")
            if not self.data:
                f.write("(Empty database)\n")
            else:
                for key in sorted(self.data.keys()):
                    f.write(f"key={key}, value={self.data[key]}\n")
        self.EnviarWeb()

    def EnviarWeb(self):
        if flask_server:
            data = {
                'type': 'node_update',
                'layer': 'core',
                'node_id': self.node_id,
                'version': self.version,
                'update_count': self.update_count,
                'data': {str(k): v for k, v in self.data.items()},
                'data_count': len(self.data)
            }
            flask_server.broadcast(data)