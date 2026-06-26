from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import secrets
import os
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path
import threading

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///horrorlauncher.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

db = SQLAlchemy(app)

# ====================== MODELS ======================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    skin_base64 = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Series(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(32), nullable=False)
    mc_version = db.Column(db.String(16), nullable=False)
    modloader = db.Column(db.String(32), nullable=False)
    modloader_version = db.Column(db.String(32), nullable=False)
    thumbnail_base64 = db.Column(db.Text, nullable=True)
    manifest_url = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    downloads = db.Column(db.Integer, default=0)

# ====================== HELPERS ======================
def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-HL-Token')
        if not token:
            return jsonify({'error': 'Token requis'}), 401
        user = User.query.filter_by(token=token).first()
        if not user:
            return jsonify({'error': 'Token invalide'}), 401
        return f(user, *args, **kwargs)
    return decorated

# ====================== AUTH ======================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Pseudo et mot de passe requis'}), 400
    if len(username) < 3 or len(username) > 16:
        return jsonify({'error': 'Pseudo entre 3 et 16 caractères'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Mot de passe trop court (min 6)'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Pseudo déjà utilisé'}), 409

    user_uuid = str(uuid.uuid4())
    user_token = secrets.token_hex(32)
    
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        uuid=user_uuid,
        token=user_token
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'username': username,
        'uuid': user_uuid,
        'token': user_token
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Identifiants incorrects'}), 401
    
    user.token = secrets.token_hex(32)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'username': user.username,
        'uuid': user.uuid,
        'token': user.token,
        'has_skin': user.skin_base64 is not None
    })

# ====================== MODS POUR LE LAUNCHER ======================
@app.route('/mods', methods=['GET'])
def get_mods():
    """Endpoint utilisé par le launcher"""
    version = request.args.get('version', '1.19.2')
    modloader = request.args.get('modloader', 'forge')
    
    series_list = Series.query.filter_by(mc_version=version, modloader=modloader).all()
    
    mods = []
    for s in series_list:
        mods.append({
            "name": s.name,
            "author": s.author,
            "url": s.manifest_url,
            "description": s.description
        })
    
    return jsonify(mods)

# ====================== SERIES ======================
@app.route('/api/series', methods=['GET'])
def get_series():
    all_series = Series.query.order_by(Series.created_at.desc()).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'author': s.author,
        'mc_version': s.mc_version,
        'modloader': s.modloader,
        'modloader_version': s.modloader_version,
        'has_thumbnail': s.thumbnail_base64 is not None,
        'manifest_url': s.manifest_url,
        'downloads': s.downloads,
        'created_at': s.created_at.isoformat()
    } for s in all_series])

@app.route('/api/series', methods=['POST'])
@require_token
def create_series(user):
    data = request.get_json()
    required = ['name', 'mc_version', 'modloader', 'modloader_version', 'manifest_url']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Champ requis: {field}'}), 400
    
    series = Series(
        name=data['name'],
        description=data.get('description', ''),
        author=user.username,
        mc_version=data['mc_version'],
        modloader=data['modloader'].lower(),
        modloader_version=data['modloader_version'],
        thumbnail_base64=data.get('thumbnail_base64'),
        manifest_url=data['manifest_url']
    )
    db.session.add(series)
    db.session.commit()
    return jsonify({'success': True, 'id': series.id}), 201

# ====================== COMPILATION LAUNCHER ======================
compilation_status = {"running": False, "success": False, "message": ""}

@app.route('/compile', methods=['GET'])
def compile_launcher():
    global compilation_status
    
    if compilation_status["running"]:
        return jsonify({"status": "running", "message": "Compilation déjà en cours..."})

    def compile_task():
        compilation_status["running"] = True
        compilation_status["message"] = "Compilation en cours..."
        
        try:
            # Installation PyInstaller
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True, timeout=60)
            
            # Nettoyage
            subprocess.run("rm -rf build dist *.spec", shell=True, cwd=os.getcwd())
            
            # Compilation
            result = subprocess.run(
                'pyinstaller --onefile --noconsole --name "Horror-Launcher" launcher.py',
                shell=True, capture_output=True, text=True, timeout=120
            )
            
            exe_path = Path("dist") / "Horror-Launcher.exe"
            if exe_path.exists():
                compilation_status["success"] = True
                compilation_status["message"] = "✅ Compilation terminée"
            else:
                compilation_status["success"] = False
                compilation_status["message"] = "Échec de la compilation"
                
        except Exception as e:
            compilation_status["success"] = False
            compilation_status["message"] = f"Erreur: {str(e)}"
        finally:
            compilation_status["running"] = False

    threading.Thread(target=compile_task, daemon=True).start()
    return jsonify({"status": "started", "message": "Compilation lancée (30-60s)"})

@app.route('/status', methods=['GET'])
def get_compilation_status():
    exe_path = Path("dist") / "Horror-Launcher.exe"
    return jsonify({
        "running": compilation_status["running"],
        "success": compilation_status["success"],
        "message": compilation_status["message"],
        "exe_ready": exe_path.exists()
    })

@app.route('/download', methods=['GET'])
def download_exe():
    exe_path = Path("dist") / "Horror-Launcher.exe"
    if exe_path.exists():
        return send_file(exe_path, as_attachment=True, download_name="Horror-Launcher.exe")
    return jsonify({"error": "EXE non trouvé"}), 404

# ====================== AUTRES ROUTES ======================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# ====================== INIT ======================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("🚀 Horror Launcher API + Compilateur démarré")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
