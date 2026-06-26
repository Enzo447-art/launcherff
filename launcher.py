import os
import sys
import requests
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading

try:
    from minecraft_launcher_lib import utils, command, install, forge
except ImportError:
    print("❌ Installe : pip install --upgrade minecraft-launcher-lib requests")
    sys.exit(1)

# Configuration
MINECRAFT_DIR = Path(utils.get_minecraft_directory()) / "horror-launcher"
MC_VERSION = "1.19.2"
FORGE_VERSION_FULL = "1.19.2-43.4.0"  # Version stable recommandée
MODS_API = "https://horror-launcher-api.onrender.com/mods"

MINECRAFT_DIR.mkdir(parents=True, exist_ok=True)


class HorrorLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Horror Launcher - 1.19.2 Forge")
        self.root.geometry("740x550")
        self.root.configure(bg="#1a0000")
        self.root.resizable(False, False)

        self.create_ui()

    def create_ui(self):
        tk.Label(self.root, text="🚀 HORROR LAUNCHER",
                 font=("Arial", 28, "bold"), fg="#ff4444", bg="#1a0000").pack(pady=15)
        tk.Label(self.root, text="Minecraft 1.19.2 Forge",
                 font=("Arial", 13), fg="#ffdddd", bg="#1a0000").pack()

        frame = tk.Frame(self.root, bg="#1a0000")
        frame.pack(pady=25, padx=50)

        self.username_var = tk.StringVar(value="HorrorPlayer")
        self.uuid_var = tk.StringVar()
        self.token_var = tk.StringVar()

        fields = [
            ("Pseudo :", self.username_var),
            ("UUID (optionnel) :", self.uuid_var),
            ("Token (optionnel) :", self.token_var)
        ]

        for i, (text, var) in enumerate(fields):
            tk.Label(frame, text=text, bg="#1a0000", fg="#ffdddd", font=("Arial", 11)).grid(
                row=i, column=0, sticky="w", pady=12, padx=10)
            tk.Entry(frame, textvariable=var, width=48, font=("Arial", 11),
                     bg="#2a2a2a", fg="white", insertbackground="white").grid(
                row=i, column=1, pady=12, padx=10)

        self.launch_btn = tk.Button(self.root, text="📥 TÉLÉCHARGER MODS & LANCER LE JEU",
                                    font=("Arial", 14, "bold"), bg="#ff4444", fg="white",
                                    width=40, height=2, command=self.start_launch)
        self.launch_btn.pack(pady=25)

        self.status = tk.Label(self.root, text="Prêt", fg="#00ff88", bg="#1a0000", font=("Arial", 11))
        self.status.pack(pady=8)

        self.progress = ttk.Progressbar(self.root, length=580, mode='indeterminate')

    def log(self, msg, color="#ffdddd"):
        self.status.config(text=msg, fg=color)

    def install_forge(self):
        self.log("🔨 Installation de Forge en cours... (ça peut prendre plusieurs minutes)", "#ffff00")
        self.progress.pack(pady=15)
        self.progress.start()

        try:
            # Installation Minecraft Vanilla
            install.install_minecraft_version(MC_VERSION, str(MINECRAFT_DIR))

            # Installation Forge (bonne méthode)
            forge_version = forge.find_forge_version(MC_VERSION)
            if forge_version:
                self.log(f"Forge trouvé : {forge_version}", "#ffff00")
                forge.install_forge_version(forge_version, str(MINECRAFT_DIR))
                self.log("✅ Forge installé avec succès !", "#00ff88")
                return True
            else:
                self.log("⚠️ Aucune version Forge trouvée", "#ffaa00")
                return False
        except Exception as e:
            self.log(f"❌ Erreur Forge: {e}", "#ff4444")
            messagebox.showerror("Erreur Forge", f"Installation échouée :\n{str(e)}\n\nEssaie de relancer.")
            return False
        finally:
            self.progress.stop()
            self.progress.pack_forget()

    def download_mods(self):
        self.log("📥 Téléchargement des mods depuis l'API...")
        try:
            r = requests.get(MODS_API, timeout=20)
            if r.status_code != 200:
                self.log("⚠️ API mods indisponible", "#ffaa00")
                return

            data = r.json() if "json" in r.headers.get("content-type", "") else []
            mods_dir = MINECRAFT_DIR / "mods"
            mods_dir.mkdir(exist_ok=True)

            for mod in data:
                if isinstance(mod, dict) and "url" in mod:
                    url = mod["url"]
                    name = url.split("/")[-1]
                    self.log(f"   → {name}")
                    with open(mods_dir / name, "wb") as f:
                        f.write(requests.get(url, timeout=30).content)
            self.log("✅ Mods téléchargés !", "#00ff88")
        except Exception as e:
            self.log(f"⚠️ Erreur mods : {e}", "#ffaa00")

    def launch_game(self):
        username = self.username_var.get().strip() or "HorrorPlayer"
        uuid = self.uuid_var.get().strip() or None
        token = self.token_var.get().strip() or None

        version_id = FORGE_VERSION_FULL

        options = {
            "username": username,
            "uuid": uuid or "00000000-0000-0000-0000-000000000000",
            "token": token or "fake-token-for-offline",
            "gameDirectory": str(MINECRAFT_DIR),
            "version": version_id,
            "maxMemory": 4096,
        }

        try:
            self.log("🚀 Lancement du jeu...", "#00ff88")
            cmd = command.get_minecraft_command(version_id, str(MINECRAFT_DIR), options)
            subprocess.Popen(cmd)
            self.root.after(2000, self.root.quit)
        except Exception as e:
            messagebox.showerror("Erreur Lancement", f"{e}\n\nVérifie que Forge est bien installé.")

    def start_launch(self):
        self.launch_btn.config(state="disabled")

        forge_installed = (MINECRAFT_DIR / "versions" / FORGE_VERSION_FULL).exists()

        if not forge_installed:
            threading.Thread(target=self.install_forge, daemon=True).start()
            self.root.after(15000, self.continue_launch)  # Attente longue pour l'installation
        else:
            self.continue_launch()

    def continue_launch(self):
        threading.Thread(target=self.download_mods, daemon=True).start()
        self.root.after(5000, self.launch_game)  # Délai pour les mods

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = HorrorLauncher()
    app.run()