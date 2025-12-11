# PArqD-Practica-4

# Sistema de Replicación Epidémica

## 📁 Estructura del Proyecto

```
epidemic_replication/
├── main.py                      # Archivo principal - ejecuta todo el sistema
├── requirements.txt             # Dependencias del proyecto
├── protos/
│   └── replication.proto        # Definición de servicios gRPC
├── generated/                   # (Se genera automáticamente)
│   ├── __init__.py
│   ├── replication_pb2.py
│   └── replication_pb2_grpc.py
├── nodes/
│   ├── __init__.py
│   ├── core_node.py             # Nodos del Core Layer (A1, A2, A3)
│   ├── layer1_node.py           # Nodos del Layer 1 (B1, B2)
│   └── layer2_node.py           # Nodos del Layer 2 (C1, C2)
└── data/
    ├── transactions.txt         # Transacciones a ejecutar
    ├── A1_log.txt               # Logs generados por cada nodo
    ├── A2_log.txt
    ├── A3_log.txt
    ├── B1_log.txt
    ├── B2_log.txt
    ├── C1_log.txt
    └── C2_log.txt
```

## 🚀 Instalación y Ejecución

### Paso 1: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 2: Ejecutar el sistema
```bash
python main.py
```

**¡Eso es todo!** El sistema automáticamente:
1. Genera el código gRPC desde el archivo .proto
2. Inicia los 7 nodos en sus respectivos puertos
3. Ejecuta las transacciones del archivo `data/transactions.txt`
4. Muestra en consola toda la actividad
5. Genera logs en archivos txt para cada nodo

## 🏗️ Arquitectura del Sistema

### Topología de Red
```
        CORE LAYER (Eager, Active, Update Everywhere)
         A1 ←→ A2 ←→ A3
         ↓      ↓      ↓
         └──→ B1     B2 ←──┘
         (cada 10 updates)
              
        LAYER 1 (Lazy, Passive)
              B1    B2
                    ↓
              (cada 10 segundos)
                    ↓
                 C1  C2
        
        LAYER 2 (Lazy, Passive)
```

### Puertos Asignados
- **A1**: 9090
- **A2**: 9091
- **A3**: 9092
- **B1**: 9093
- **B2**: 9094
- **C1**: 9095
- **C2**: 9096

## 📝 Formato de Transacciones

El archivo `data/transactions.txt` contiene transacciones con este formato:

### Transacciones de Escritura (Write)
```
b, w(key,value), w(key,value), r(key), c
```
- `b`: Begin transaction (siempre en Core Layer)
- `w(key,value)`: Write operation
- `r(key)`: Read operation
- `c`: Commit transaction

### Transacciones de Solo Lectura (Read-Only)
```
b<layer>, r(key), r(key), c
```
- `b0`: Begin en Core Layer (A1, A2, A3)
- `b1`: Begin en Layer 1 (B1, B2)
- `b2`: Begin en Layer 2 (C1, C2)
- `r(key)`: Read operation
- `c`: Commit transaction

### Ejemplo de Transacciones
```
b, w(10,100), w(20,200), c          # Escribe en Core Layer
b0, r(10), r(20), c                 # Lee desde Core Layer
b1, r(10), r(20), c                 # Lee desde Layer 1
b2, r(10), r(20), c                 # Lee desde Layer 2
```

## 🔄 Estrategias de Replicación

### Core Layer (A1, A2, A3)
- **Update Everywhere**: Cualquier nodo puede recibir escrituras
- **Eager Replication**: Los cambios se propagan inmediatamente a otros nodos del core
- **Active Replication**: Todos los nodos procesan las mismas operaciones

### Layer 1 (B1, B2)
- **Lazy Replication**: Reciben datos **cada 10 updates** desde el core
- **Passive Replication**: Reciben el estado resultante, no las operaciones
- **Primary Backup**: A2 → B1, A3 → B2

### Layer 2 (C1, C2)
- **Lazy Replication**: Reciben datos **cada 10 segundos** desde layer 1
- **Passive Replication**: Reciben el estado resultante
- **Primary Backup**: B2 → C1, B2 → C2

## 📊 Verificar el Funcionamiento

### Consola
Verás mensajes como:
```
[A1] WRITE key=10, value=100, version=1, update_count=1
[A1] Synced with A2, version=1
[A2] Received update from core, version=1
[A2] Propagating to Layer 1 (update count: 10)
[B1] Received update from layer 1, version=10
[B2] Propagating to Layer 2 (timer: 10s)
[C1] Received update from layer 2, version=10
```

### Archivos de Log
Revisa los archivos en `data/`:
- `A1_log.txt`, `A2_log.txt`, `A3_log.txt`: Logs del core
- `B1_log.txt`, `B2_log.txt`: Logs de layer 1
- `C1_log.txt`, `C2_log.txt`: Logs de layer 2

Cada log muestra:
```
=== Node A1 Log ===
Version 0: Empty database
Version 1: key=10, value=100
Version 2: key=20, value=200
```

## 🛠️ Personalización

### Modificar Transacciones
Edita `data/transactions.txt` con tus propias transacciones.

### Cambiar Puertos
Modifica el diccionario `ports` en `main.py`:
```python
ports = {
    'A1': 9090,
    'A2': 9091,
    # ... etc
}
```

### Ajustar Tiempos de Propagación
En `layer1_node.py`, línea 52:
```python
time.sleep(10)  # Cambiar a tu preferencia
```

En `core_node.py`, línea 61:
```python
if self.update_count % 10 == 0:  # Cambiar el 10 por otro número
```

## ❌ Detener el Sistema
Presiona `Ctrl+C` en la terminal donde ejecutaste `main.py`

## 🐛 Troubleshooting

### Error: "No module named 'grpc'"
```bash
pip install grpcio grpcio-tools
```

### Error: "Port already in use"
Algún puerto está ocupado. Cambia los puertos en `main.py` o mata el proceso:
```bash
# En Windows
netstat -ano | findstr :9090
taskkill /PID <PID> /F

# En Linux/Mac
lsof -ti:9090 | xargs kill -9
```

### Los logs no se generan
Asegúrate de que existe el directorio `data/`:
```bash
mkdir data
```

## 📚 Conceptos Implementados

✅ **Eager Replication** (Core Layer)
✅ **Lazy Replication** (Layer 1 y 2)
✅ **Active Replication** (State Machine en Core)
✅ **Passive Replication** (Primary-Backup en Layers)
✅ **Update Everywhere** (Core acepta writes en cualquier nodo)
✅ **Primary Copy** (Layers reciben desde un nodo específico)
✅ **Eventual Consistency** (Los datos convergen con el tiempo)

## 📈 Próximos Pasos

1. **Interfaz Web**: Añadir monitorización en tiempo real con WebSockets
2. **Manejo de Fallos**: Implementar detección y recuperación de nodos caídos
3. **Conflictos**: Gestión de conflictos en escrituras concurrentes
4. **Persistencia**: Guardar datos en base de datos real
5. **Métricas**: Latencia, throughput, consistencia

---

**Autor**: Tu nombre
**Curso**: Distributed Systems 2025-2026
**Fecha**: Diciembre 2025