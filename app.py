from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sifiki_master_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discord_final.db'

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager(app)
login_manager.login_view = 'index'

# --- MODELOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    avatar = db.Column(db.Text)
    role = db.Column(db.String(20))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    sender = db.Column(db.String(50))
    channel = db.Column(db.String(50))
    m_type = db.Column(db.String(10)) # text, image, video
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('chat.html')
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.form
    pfp = request.files.get('pfp')
    # Convertir imagen a base64 para la DB
    avatar_data = ""
    if pfp:
        import base64
        avatar_data = f"data:{pfp.content_type};base64,{base64.b64encode(pfp.read()).decode()}"
    
    role = 'owner' if data['username'].lower() == 'sifiki' else 'user'
    hashed = generate_password_hash(data['password'])
    
    new_user = User(username=data['username'], email=data['email'], password=hashed, avatar=avatar_data, role=role)
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(email=request.form['email']).first()
    if user and check_password_hash(user.password, request.form['password']):
        login_user(user)
    return redirect(url_for('index'))

# --- SOCKETS ---
usuarios_conectados = {}

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        usuarios_conectados[current_user.username] = {
            'role': current_user.role,
            'avatar': current_user.avatar
        }
        emit('update_user_list', usuarios_conectados, broadcast=True)

@socketio.on('join')
def on_join(data):
    room = data['channel']
    join_room(room)
    msgs = Message.query.filter_by(channel=room).order_by(Message.id.desc()).limit(30).all()
    for m in reversed(msgs):
        u = User.query.filter_by(username=m.sender).first()
        emit('message', {
            'user': m.sender, 'msg': m.content, 'type': m.m_type,
            'avatar': u.avatar if u else '', 'role': u.role if u else 'user',
            'channel': room, 'time': m.timestamp.strftime('%H:%M')
        })

@socketio.on('chat-msg')
def handle_msg(data):
    nuevo = Message(content=data['msg'], sender=current_user.username, channel=data['channel'], m_type=data.get('type', 'text'))
    db.session.add(nuevo)
    db.session.commit()
    data['user'] = current_user.username
    data['avatar'] = current_user.avatar
    data['role'] = current_user.role
    data['time'] = datetime.datetime.now().strftime('%H:%M')
    emit('message', data, to=data['channel'])

if __name__ == '__main__':
    socketio.run(app, debug=True)
