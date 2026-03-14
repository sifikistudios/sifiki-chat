from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sifiki_secret_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Modelo de la base de datos
class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.String(500), nullable=False)

# Crear la base de datos al iniciar
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# Busca la función handle_message y cámbiala por esta:
@socketio.on('message')
def handle_message(data):
    # 'data' ahora será un diccionario: {'usuario': 'paco', 'msg': 'hola'}
    nombre = data.get('usuario', 'Anónimo')
    mensaje_texto = data.get('msg', '')
    
    contenido_final = f"{nombre}: {mensaje_texto}"
    
    # Guardar en la base de datos
    nuevo_mensaje = Mensaje(contenido=contenido_final)
    db.session.add(nuevo_mensaje)
    db.session.commit()
    
    # Enviar a todos
    send(data, broadcast=True)

@socketio.on('connect')
def handle_connect():
    # Enviar los últimos 10 mensajes al nuevo usuario que entra
    ultimos_mensajes = Mensaje.query.order_by(Mensaje.id.desc()).limit(10).all()
    for msg in reversed(ultimos_mensajes):
        send(msg.contenido)

if __name__ == '__main__':
    socketio.run(app, debug=True)
