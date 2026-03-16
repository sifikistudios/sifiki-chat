from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sifiki_discord_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sifiki_discord.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- MODELO DE BASE DE DATOS MEJORADO ---
class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    canal = db.Column(db.String(50), nullable=False)
    msg = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# --- LÓGICA DE CANALES (JOIN) ---
@socketio.on('join')
def on_join(data):
    username = data.get('user', 'Anónimo')
    room = data.get('channel', 'general')
    
    join_room(room)
    
    # Enviar historial solo de ese canal
    historial = Mensaje.query.filter_by(canal=room).order_by(Mensaje.id.desc()).limit(20).all()
    for m in reversed(historial):
        emit('message', {
            'user': m.usuario,
            'role': m.rol,
            'msg': m.msg,
            'channel': m.canal,
            'time': m.timestamp.strftime('%H:%M')
        })

# --- MANEJO DE MENSAJES ---
@socketio.on('chat-msg')
def handle_chat_message(data):
    # Extraer datos del JSON enviado por el frontend
    usuario = data.get('user')
    rol = data.get('role')
    msg_texto = data.get('msg')
    canal = data.get('channel')
    hora_actual = datetime.datetime.now().strftime('%H:%M')

    # Guardar en DB de forma estructurada
    nuevo_msg = Mensaje(
        usuario=usuario,
        rol=rol,
        canal=canal,
        msg=msg_texto
    )
    db.session.add(nuevo_msg)
    db.session.commit()

    # Añadir la hora para el frontend
    data['time'] = hora_actual

    # Emitir SOLO al canal correspondiente (room)
    emit('message', data, to=canal)

if __name__ == '__main__':
    socketio.run(app, debug=True)
