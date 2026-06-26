from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///horrorlauncher.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'horror-secret-key')

db = SQLAlchemy(app)

# Modèle pour le modpack
class ModPack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zip_url = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ====================== PAGES ======================
@app.route('/')
def index():
    return render_template('index.html')

# ====================== MODS API (pour le launcher) ======================
@app.route('/mods', methods=['GET'])
def get_mods():
    pack = ModPack.query.first()
    if pack:
        return jsonify([{
            "name": "horror-modpack.zip",
            "url": pack.zip_url,
            "is_zip": True
        }])
    return jsonify([])

# ====================== TÉLÉCHARGEMENT DIRECT ======================
@app.route('/download', methods=['GET'])
def download_launcher():
    exe_path = Path("static") / "Horror-Launcher.exe"
    if exe_path.exists():
        return send_file(exe_path, as_attachment=True, download_name="Horror-Launcher.exe")
    return "❌ Launcher EXE non trouvé", 404

@app.route('/modpack', methods=['GET'])
def download_modpack():
    zip_path = Path("static") / "horror-modpack.zip"
    if zip_path.exists():
        return send_file(zip_path, as_attachment=True, download_name="horror-modpack.zip")
    return "❌ Modpack ZIP non trouvé", 404

# ====================== CONFIGURER LE ZIP (une seule fois) ======================
@app.route('/api/modpack', methods=['POST'])
def set_modpack():
    data = request.get_json()
    if not data or not data.get('zip_url'):
        return jsonify({'error': 'zip_url requis'}), 400
    
    ModPack.query.delete()
    pack = ModPack(zip_url=data['zip_url'])
    db.session.add(pack)
    db.session.commit()
    return jsonify({'success': True, 'zip_url': data['zip_url']})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# ====================== INIT ======================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("🚀 Horror Launcher API démarrée")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
