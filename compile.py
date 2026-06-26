import os
import shutil
import sys
from pathlib import Path

def clean_previous_build():
    """Nettoie les anciens fichiers de compilation"""
    for folder in ["build", "dist", "__pycache__"]:
        if Path(folder).exists():
            try:
                shutil.rmtree(folder)
                print(f"🧹 Nettoyage de {folder}/")
            except:
                pass
    # Supprime les fichiers temporaires
    for file in ["Horror-Launcher.spec"]:
        if Path(file).exists():
            try:
                os.remove(file)
                print(f"🧹 Suppression de {file}")
            except:
                pass

def compile_launcher():
    print("=" * 60)
    print("🔨 Lancement de la compilation Horror Launcher...")
    print("=" * 60)

    if not Path("launcher.py").exists():
        print("❌ ERREUR: launcher.py non trouvé dans le dossier !")
        sys.exit(1)

    clean_previous_build()

    print("📦 Compilation avec PyInstaller (onefile + sans console)...")

    # Commande de compilation optimisée
    command = (
        'pyinstaller '
        '--onefile '
        '--noconsole '
        '--name "Horror-Launcher" '
        '--clean '
        '--add-data "launcher.py;." '  # Au cas où
        'launcher.py'
    )

    result = os.system(command)

    exe_path = Path("dist") / "Horror-Launcher.exe"

    if exe_path.exists():
        print("\n✅ COMPILATION RÉUSSIE !")
        print(f"📍 EXE créé ici : {exe_path.absolute()}")
        print(f"📏 Taille : {exe_path.stat().st_size / (1024*1024):.1f} MB")
        print("\n🎉 Tu peux maintenant distribuer cet EXE !")
        
        # Ouvrir le dossier dist automatiquement (Windows)
        try:
            os.startfile(exe_path.parent)
        except:
            pass
    else:
        print("\n❌ ÉCHEC DE LA COMPILATION")
        print("Conseils :")
        print("   1. Vérifie que PyInstaller est installé : pip install pyinstaller")
        print("   2. Essaie de relancer le script")
        print("   3. Vérifie que launcher.py fonctionne seul avec 'python launcher.py'")

if __name__ == "__main__":
    compile_launcher()