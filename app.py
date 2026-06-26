from flask import Flask, render_template, send_file
import os
import threading
import time
from compile import compile_launcher

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile')
def compile_and_download():
    def compile_task():
        compile_launcher()
    
    thread = threading.Thread(target=compile_task)
    thread.start()
    
    time.sleep(10)  # Attente pour que la compilation commence
    
    exe_path = "dist/Horror-Launcher.exe"
    if os.path.exists(exe_path):
        return send_file(exe_path, as_attachment=True)
    else:
        return "Compilation en cours... Rafraîchis la page dans 20-30 secondes.", 202

if __name__ == '__main__':
    print("🚀 Serveur lancé → http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=5000)