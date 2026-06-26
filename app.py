from flask import Flask, request, jsonify, send_file, render_template
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
import sys

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

# ====================== PAGE D'ACCUEIL ======================
@app.route('/')
def index():
    return render_template('index.html')

# ====================== MODS POUR LE LAUNCHER ======================
@app.route('/mods', methods=['GET'])
def get_mods():
    version = request.args.get('version', '1.19.2')
    modloader = request.args.get('modloader', 'forge')
    
    series_list = Series.query.filter_by(mc_version=version, modloader=modloader).all()
    
    mods = []
    for s in series_list:
        mods.append({
            "name": s.name,
            "author": s.author,
            "url": s.manifest_url,
            "description": s.description or ""
        })
    return jsonify(mods)

# ====================== COMPILATION ======================
compilation_status = {"running": False, "success": False, "message": ""}

@app.route('/compile', methods=['GET'])
def compile_launcher():
    global compilation_status
    if compilation_status["running"]:
        return jsonify({"status": "running", "message": "Compilation déjà en cours"})

    def compile_task():
        compilation_status["running"] = True
        compilation_status["message"] = "Démarrage de la compilation..."
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True, timeout=60)
            subprocess.run("rm -rf build dist *.spec", shell=True, cwd=os.getcwd())
            
            result = subprocess.run(
                'pyinstaller --onefile --noconsole --name "Horror-Launcher" launcher.py',
                shell=True, capture_output=True, text=True, timeout=180
            )
            
            exe_path = Path("dist") / "Horror-Launcher.exe"
            if exe_path.exists():
                compilation_status["success"] = True
                compilation_status["message"] = "✅ Compilation terminée avec succès"
            else:
                compilation_status["success"] = False
                compilation_status["message"] = "❌ Échec de compilation"
        except Exception as e:
            compilation_status["success"] = False
            compilation_status["message"] = f"Erreur: {str(e)}"
        finally:
            compilation_status["running"] = False

    threading.Thread(target=compile_task, daemon=True).start()
    return jsonify({"status": "started", "message": "Compilation lancée... (30 à 60 secondes)"})

@app.route('/status', methods=['GET'])
def get_status():
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
    return jsonify({"error": "EXE non prêt"}), 404

# ====================== AUTRES ROUTES (auth, series, etc.) ======================
# ... (tu peux remettre tes routes register, login, series ici)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# ====================== INIT ======================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("🚀 Serveur Horror Launcher démarré sur http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
