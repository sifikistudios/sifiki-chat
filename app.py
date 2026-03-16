from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sifiki_secure_key_88'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discord_pro.db'

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=20 * 1024 * 1024)

# MODELO DE USUARIO
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.Text, nullable=True) # Base64 de la foto
    role = db.Column(db.String(20), default='user')

# MODELO DE MENSAJES
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    sender = db.Column(db.String(50))
    channel = db.Column(db.String(50))
    m_type = db.Column(db.String(10)) # 'text', 'image', 'video'
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# --- EVENTOS DE SOCKET ---
@socketio.on('register')
def handle_register(data):
    hashed_pw = generate_password_hash(data['password'], method='pbkdf2:sha256')
    role = 'owner' if data['username'].lower() == 'sifiki' else 'user'
    
    try:
        new_user = User(username=data['username'], email=data['email'], password=hashed_pw, avatar=data['avatar'], role=role)
        db.session.add(new_user)
        db.session.commit()
        emit('auth_response', {'status': 'success', 'user': data['username'], 'role': role, 'avatar': data['avatar']})
    except:
        emit('auth_response', {'status': 'error', 'msg': 'Usuario o correo ya existe'})

@socketio.on('login')
def handle_login(data):
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password, data['password']):
        emit('auth_response', {'status': 'success', 'user': user.username, 'role': user.role, 'avatar': user.avatar})
    else:
        emit('auth_response', {'status': 'error', 'msg': 'Credenciales incorrectas'})

@socketio.on('join')
def on_join(data):
    room = data['channel']
    join_room(room)
    # Cargar últimos 20 mensajes del canal
    msgs = Message.query.filter_by(channel=room).order_by(Message.id.desc()).limit(20).all()
    for m in reversed(msgs):
        # Necesitamos buscar el avatar del emisor
        u = User.query.filter_by(username=m.sender).first()
        emit('message', {'user': m.sender, 'msg': m.content, 'type': m.m_type, 'avatar': u.avatar if u else None, 'role': u.role if u else 'user', 'channel': room})

@socketio.on('chat-msg')
def handle_msg(data):
    new_m = Message(content=data['msg'], sender=data['user'], channel=data['channel'], m_type=data.get('type', 'text'))
    db.session.add(new_m)
    db.session.commit()
    emit('message', data, to=data['channel'])

if __name__ == '__main__':
    socketio.run(app, debug=True)
