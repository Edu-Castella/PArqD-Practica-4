from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import threading

app = Flask(__name__, static_folder='web', template_folder='web')
app.config['SECRET_KEY'] = 'practica4'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


class FlaskWebServer:
    def __init__(self, port=8080):
        self.port = port
        self.thread = None
        self.socketio = socketio

    def broadcast(self, data):
        try:
            if isinstance(data, dict):
                self.socketio.emit('node_update', data, namespace='/')
        except Exception as e:
            pass

    def start(self):
        def run():
            self.socketio.run(
                app,
                host='0.0.0.0',
                port=self.port,
                allow_unsafe_werkzeug=True,
                debug=False,
                use_reloader=False
            )

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        print("Aturant servidor...")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

flask_server = FlaskWebServer()