import webview
import subprocess
import psutil
import time
import socket
import sys
import os

def is_n8n_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            # On Windows, node processes n8n usually have 'n8n' in the command line
            if proc.info['name'] and 'node' in proc.info['name'].lower():
                if proc.info['cmdline'] and any('n8n' in arg.lower() for arg in proc.info['cmdline']):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def check_command(cmd):
    try:
        # Use 'where' on Windows to check if command exists
        result = subprocess.run(f"where {cmd}", shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

def start_n8n_logic(window):
    time.sleep(1) # Small delay for UI to settle
    
    # 1. Check if already running
    if is_n8n_running():
        window.evaluate_js("updateStatus('n8n est déjà en cours d\\'exécution. Connexion...')")
    else:
        # 2. Check installation
        cmd = ""
        if check_command("n8n"):
            cmd = "n8n start"
        elif check_command("npx"):
            cmd = "npx n8n start"
        else:
            window.evaluate_js("showError('ERREUR : n8n n\\'est pas installé sur ce système (ni n8n, ni npx trouvés).')")
            return

        # 3. Launch in background
        window.evaluate_js(f"updateStatus('Lancement de n8n via : {cmd}...')")
        try:
            # CREATE_NO_WINDOW = 0x08000000 to hide terminal on Windows
            subprocess.Popen(cmd, shell=True, creationflags=0x08000000)
        except Exception as e:
            window.evaluate_js(f"showError('Erreur de lancement : {str(e)}')")
            return

    # 4. Wait for port 5678 to be active
    timeout = 90
    start_time = time.time()
    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time
        progress = min(int((elapsed / 30) * 100), 99) # Visual progress over approx 30s
        window.evaluate_js(f"updateProgress({progress})")
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(('127.0.0.1', 5678)) == 0:
                window.evaluate_js("updateProgress(100)")
                window.evaluate_js("updateStatus('Chargement de l\\'interface...')")
                time.sleep(0.5)
                window.load_url("http://localhost:5678")
                return
        time.sleep(1)
    
    window.evaluate_js("showError('Délai d\\'attente dépassé. n8n met trop de temps à démarrer ou a échoué.')")

html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center; 
            height: 100vh; 
            margin: 0;
            background: #1a1b26; 
            color: white;
        }
        .container { text-align: center; width: 80%; max-width: 400px; }
        .logo { font-size: 48px; font-weight: bold; margin-bottom: 20px; color: #ff6d5a; }
        .loader { 
            border: 4px solid #24283b; 
            border-top: 4px solid #ff6d5a; 
            border-radius: 50%; 
            width: 50px; 
            height: 50px; 
            animation: spin 1s linear infinite; 
            margin: 0 auto 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .progress-container { 
            width: 100%; 
            background: #24283b; 
            border-radius: 20px; 
            height: 10px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-bar { 
            width: 0%; 
            height: 100%; 
            background: linear-gradient(90deg, #ff6d5a, #ffa26c); 
            transition: width 0.4s ease; 
        }
        #status { margin-top: 20px; font-size: 14px; color: #a9b1d6; }
        #error-box { 
            background: #414868; 
            border-left: 5px solid #f7768e; 
            padding: 15px; 
            margin-top: 20px; 
            display: none; 
            color: #f7768e;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container" id="main-ui">
        <div class="logo">n8n Launcher</div>
        <div class="loader"></div>
        <div class="progress-container"><div id="bar" class="progress-bar"></div></div>
        <div id="status">Initialisation...</div>
        <div id="error-box"></div>
    </div>
    <script>
        function updateStatus(msg) { document.getElementById('status').innerText = msg; }
        function updateProgress(p) { document.getElementById('bar').style.width = p + '%'; }
        function showError(msg) { 
            document.querySelector('.loader').style.display = 'none';
            document.querySelector('.progress-container').style.display = 'none';
            document.getElementById('status').style.display = 'none';
            const err = document.getElementById('error-box');
            err.innerText = msg;
            err.style.display = 'block';
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    window = webview.create_window(
        'n8n Desktop', 
        html=html_content, 
        width=1280, 
        height=800, 
        background_color='#1a1b26'
    )
    webview.start(start_n8n_logic, window)
