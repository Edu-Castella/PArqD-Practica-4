import grpc
from concurrent import futures
import threading
import time
import sys
import os
from protos import replication_pb2, replication_pb2_grpc
from web import flask_server

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Layer1Node(replication_pb2_grpc.ReplicationServiceServicer):
    def __init__(self, id, port, layer2_ports, data_dir):
        self.id = id
        self.port = port
        self.layer2_ports = layer2_ports
        self.data = {}
        self.versio = 0
        self.log_file = os.path.join(data_dir, f"{id}_log.txt")
        self.server = None
        self.propagation_timer = None

        with open(self.log_file, 'w') as f:
            f.write(f"LOG NODE {id}\n")
            f.write(f"Versio 0: BUIT\n")

        self.PropagacioTimer()

    def Read(self, request, context):
        key = request.key
        if key in self.data:
            value = self.data[key]
            return replication_pb2.ReadResponse(valor=value, ack=True, missatge="OK")
        else:
            return replication_pb2.ReadResponse(valor=0, ack=False, missatge="Key no trobada")

    def PropagateOtherLayers(self, request, context):
        for key, valor in request.data.items():
            self.data[key] = valor

        self.versio = request.versio

        self.WriteLog()

        return replication_pb2.PropagateOtherLayersResponse(ack=True)

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
                    request = replication_pb2.PropagateOtherLayersRequest(
                        data=self.data,
                        versio=self.versio
                    )
                    response = stub.PropagateOtherLayers(request, timeout=2)
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
            f.write(f"\nVersio {self.versio}\n")
            if not self.data:
                f.write("(Buit)\n")
            else:
                for key in sorted(self.data.keys()):
                    f.write(f"Key={key}, Valor={self.data[key]}\n")

        self.EnviarWeb()

    def EnviarWeb(self):
        if flask_server:
            data = {
                'type': 'node_update',
                'layer': '1',
                'id': self.id,
                'versio': self.versio,
                'data': {str(k): v for k, v in self.data.items()},
                'count_data': len(self.data)
            }
            flask_server.broadcast(data)