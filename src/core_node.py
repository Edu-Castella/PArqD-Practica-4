import grpc
from concurrent import futures
import sys
import os
from protos import replication_pb2, replication_pb2_grpc
from web import flask_server

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CoreNode(replication_pb2_grpc.ReplicationServiceServicer):
    def __init__(self, id, port, other_ports, layer1_ports, data_dir):
        self.id = id
        self.port = port
        self.other_ports = other_ports
        self.layer1_ports = layer1_ports
        self.data = {}
        self.versio = 0
        self.count_act = 0
        self.logs = os.path.join(data_dir, f"{id}_log.txt")
        self.server = None

        with open(self.logs, 'w') as f:
            f.write(f"LOG NODE {id}\n")
            f.write(f"Versio 0: BUIT\n")

    def Read(self, request, context):
        key = request.key
        if key in self.data:
            value = self.data[key]
            return replication_pb2.ReadResponse(valor=value, ack=True, missatge="OK")
        else:
            return replication_pb2.ReadResponse(valor=0, ack=False, missatge="Key no trobada")

    def Write(self, request, context):
        key = request.key
        value = request.valor

        self.data[key] = value
        self.versio += 1
        self.count_act += 1

        self.WriteLog()

        self.PropagarCoreNodes()

        if self.count_act % 10 == 0:
            self.PropagarLayer1()

        return replication_pb2.WriteResponse(ack=True, missatge="Write successful")


    def PropagateCoreNodes(self, request, context):
        for key, valor in request.data.items():
            self.data[key] = valor

        if request.versio > self.versio:
            self.versio = request.versio
            self.count_act = request.versio

        self.WriteLog()

        if self.count_act > 0 and self.count_act % 10 == 0 and self.layer1_ports:
            self.PropagarLayer1()

        return replication_pb2.PropagateCoreNodesResponse(ack=True)

    def PropagarCoreNodes(self):
        for other_port in self.other_ports:
            try:
                with grpc.insecure_channel(f'localhost:{other_port}') as channel:
                    stub = replication_pb2_grpc.ReplicationServiceStub(channel)
                    request = replication_pb2.PropagateCoreNodesRequest(
                        data=self.data,
                        versio=self.versio,
                        id_send=self.id
                    )
                    stub.PropagateCoreNodes(request, timeout=2)
            except Exception as e:
                pass

    def PropagarLayer1(self):
        if not self.layer1_ports:
            return

        for layer1_port in self.layer1_ports:
            try:
                with grpc.insecure_channel(f'localhost:{layer1_port}') as channel:
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
        with open(self.logs, 'a') as f:
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
                'layer': '0',
                'id': self.id,
                'versio': self.versio,
                'count_act': self.count_act,
                'data': {str(k): v for k, v in self.data.items()},
                'count_data': len(self.data)
            }
            flask_server.broadcast(data)