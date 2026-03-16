from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sifiki_ultra_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discord_sifiki.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10 * 1024 * 1024) # Soporte para archivos de 10MB

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50))
    rol = db.Column(db.String(20))
    canal = db.Column(db.String(50))
    tipo = db.Column(db.String(10), default='text') # 'text', 'image', 'video'
    msg = db.Column(db.Text) 
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def on_join(data):
    room = data['channel']
    join_room(room)
    # Cargar historial del canal o DM
    historial = Mensaje.query.filter_by(canal=room).order_by(Mensaje.id.desc()).limit(30).all()
    for m in reversed(historial):
        emit('message', {
            'user': m.usuario, 'role': m.rol, 'msg': m.msg,
            'type': m.tipo, 'channel': m.canal, 'time': m.timestamp.strftime('%H:%M')
        })

@socketio.on('chat-msg')
def handle_msg(data):
    data['time'] = datetime.datetime.now().strftime('%H:%M')
    nuevo = Mensaje(
        usuario=data['user'], rol=data['role'], canal=data['channel'],
        tipo=data.get('type', 'text'), msg=data['msg']
    )
    db.session.add(nuevo)
    db.session.commit()
    emit('message', data, to=data['channel'])

if __name__ == '__main__':
    socketio.run(app, debug=True)
