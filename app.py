from flask import Flask, render_template, send_file, jsonify
import os
import threading
import time
from pathlib import Path
from compile import compile_launcher

app = Flask(__name__)

# Variable globale pour suivre l'état de la compilation
compilation_status = {"running": False, "success": False, "message": ""}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile')
def compile_and_download():
    global compilation_status
    
    # Si une compilation est déjà en cours
    if compilation_status["running"]:
        return jsonify({"status": "running", "message": "Compilation déjà en cours..."})

    # Lancer la compilation dans un thread
    def compile_task():
        compilation_status["running"] = True
        compilation_status["success"] = False
        compilation_status["message"] = "Compilation démarrée..."
        
        try:
            success = compile_launcher()
            compilation_status["success"] = success
            compilation_status["message"] = "Compilation terminée" if success else "Échec de la compilation"
        except Exception as e:
            compilation_status["success"] = False
            compilation_status["message"] = f"Erreur: {str(e)}"
        finally:
            compilation_status["running"] = False

    thread = threading.Thread(target=compile_task)
    thread.start()

    return jsonify({
        "status": "started",
        "message": "Compilation lancée... Attends 20 à 45 secondes"
    })

@app.route('/status')
def get_status():
    """Permet de vérifier l'état de la compilation"""
    global compilation_status
    exe_path = Path("dist") / "Horror-Launcher.exe"
    
    if exe_path.exists() and not compilation_status["running"]:
        compilation_status["success"] = True
    
    return jsonify({
        "running": compilation_status["running"],
        "success": compilation_status["success"],
        "message": compilation_status["message"],
        "exe_ready": exe_path.exists()
    })

@app.route('/download')
def download_exe():
    """Télécharge l'EXE une fois prêt"""
    exe_path = Path("dist") / "Horror-Launcher.exe"
    if exe_path.exists():
        return send_file(exe_path, as_attachment=True, download_name="Horror-Launcher.exe")
    else:
        return "L'EXE n'est pas encore prêt. Rafraîchis dans quelques secondes.", 404

if __name__ == '__main__':
    print("🚀 Serveur Horror Launcher démarré sur http://localhost:5000")
    print("   → Clique sur le bouton pour compiler")
    app.run(debug=False, host='0.0.0.0', port=5000)
