# PArqD-Practica-4

Aquest és el README de la nostra pràctica 4 de Projectes en arquitectura distribuïda.
- Eduard Castellà (e.castella)
- Álvaro Barrado (alvaro.barrado)
## Estructura del projecte

```
PArqD-Practica-4/
├── main.py                    
├── requirements.txt
├── web.py
├── README.md
├── .gitignore      
├── protos/
│   ├── __init__.py
│   ├── replication.proto
│   ├── replication_pb2.py
│   └── replication_pb2_grpc.py
├── src/
│   ├── __init__.py
│   ├── core_node.py
│   ├── layer1_node.py
│   └── layer2_node.py
├── data/
│   ├── transactions.txt
│   ├── A1_log.txt
│   ├── A2_log.txt
│   ├── A3_log.txt
│   ├── B1_log.txt
│   ├── B2_log.txt
│   ├── C1_log.txt
│   └── C2_log.txt
└── web/
    └── index.html
```

## Execució

### 1. Generar codi gRPC
```bash
 python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. .\protos\replication.proto
```

### 2. Instal·lar dependències
```bash
pip install -r requirements.txt
```

### 3: Executar
```bash
python main.py
```
o prémer el botó de "Run".