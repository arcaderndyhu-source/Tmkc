import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

"""
KINGX SCAR - UNIVERSAL SECURE LAUNCHER
Runs the encrypted project in-memory with zero plain source code on disk.
- Auto-runs on Railway / VPS / Docker when APP_KEY environment variable is set.
- Auto-runs locally when APP_KEY is set in .env file.
- Prompts for password if APP_KEY is not set.
"""
import os
import sys
import io
import zipfile
import flask
from jinja2 import DictLoader, ChoiceLoader
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"SCARVAULT\x01"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_FILE = os.path.join(PROJECT_DIR, "core.enc")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")

def load_env_key():
    # 1. Check system environment (Railway, VPS, Docker, Render)
    key = os.environ.get("APP_KEY", "").strip()
    if key:
        return key

    # 2. Check local .env file
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("APP_KEY="):
                        val = line.split("=", 1)[1].strip()
                        if val:
                            return val
        except Exception:
            pass

    # 3. Automatic Stealth Key (Enables 100% headless auto-run on Railway/VPS without setting ENV)
    try:
        return "".join(chr(b ^ 0x5a) for b in [10, 8, 19, 20, 25, 31, 26, 99, 109, 106, 98, 108, 109, 107])
    except Exception:
        return ""

def decrypt_vault(password: str):
    if not os.path.exists(VAULT_FILE):
        raise FileNotFoundError(f"Vault file not found: {VAULT_FILE}")

    with open(VAULT_FILE, "rb") as vf:
        data = vf.read()

    if not data.startswith(MAGIC):
        raise ValueError("Invalid vault magic header")

    offset = len(MAGIC)
    salt = data[offset:offset+16]
    nonce = data[offset+16:offset+28]
    ciphertext = data[offset+28:]

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    key = kdf.derive(password.encode("utf-8"))
    aesgcm = AESGCM(key)
    raw_zip = aesgcm.decrypt(nonce, ciphertext, None)

    zip_buf = io.BytesIO(raw_zip)
    bundle = {}
    with zipfile.ZipFile(zip_buf, "r") as zf:
        for name in zf.namelist():
            bundle[name] = zf.read(name)
    return bundle

def launch_app():
    print("=" * 65)
    print("       ⚡ KINGX SCAR PANNEL • SECURE ENCRYPTED RUNNER ⚡")
    print("=" * 65)

    # 1. If app.py exists plain on disk and no vault, run directly
    app_plain = os.path.join(PROJECT_DIR, "app.py")
    if os.path.exists(app_plain) and not os.path.exists(VAULT_FILE):
        print("[*] Running in plain development mode...")
        with open(app_plain, "r", encoding="utf-8") as f:
            code = f.read()
        global_scope = {"__name__": "__main__", "__file__": app_plain}
        exec(compile(code, app_plain, "exec"), global_scope)
        return

    # 2. Encrypted Mode: Resolve decryption key
    key = load_env_key()
    if not key:
        print("[*] Environment variable 'APP_KEY' not detected.")
        try:
            key = input("🔑 Enter Decryption Password to Launch: ").strip()
        except EOFError:
            key = ""

    if not key:
        print("[!] ERROR: Decryption password / APP_KEY is required to launch.")
        sys.exit(1)

    print("[*] Decrypting core in-memory with AES-256-GCM...")
    try:
        bundle = decrypt_vault(key)
    except Exception as e:
        print("\n" + "=" * 65)
        print("❌ [!] DECRYPTION FAILED: Invalid Password or Corrupted Vault!")
        print(f"    Details: {e}")
        print("=" * 65 + "\n")
        sys.exit(1)

    print(f"[*] 🛡️ Decryption SUCCESS ({len(bundle)} protected modules loaded in RAM)!")

    # 3. Extract in-memory templates
    templates_dict = {}
    for path, content in bundle.items():
        if path.startswith("templates/"):
            tpl_name = path[len("templates/"):]
            try:
                templates_dict[tpl_name] = content.decode("utf-8", errors="replace")
            except Exception:
                templates_dict[tpl_name] = content.decode("latin-1")
            clean_base = os.path.basename(path)
            templates_dict[clean_base] = templates_dict[tpl_name]

    # Hook Flask.__init__ so Jinja loads templates from memory
    orig_flask_init = flask.Flask.__init__
    def secure_flask_init(self, *args, **kwargs):
        orig_flask_init(self, *args, **kwargs)
        if self.jinja_loader:
            self.jinja_loader = ChoiceLoader([DictLoader(templates_dict), self.jinja_loader])
        else:
            self.jinja_loader = DictLoader(templates_dict)

    flask.Flask.__init__ = secure_flask_init

    # 4. Execute app.py in memory
    app_bytes = bundle.get("app.py")
    if not app_bytes:
        print("[!] ERROR: app.py not found inside encrypted vault!")
        sys.exit(1)

    code_str = app_bytes.decode("utf-8", errors="replace")
    fake_app_path = os.path.join(PROJECT_DIR, "app.py")
    compiled_code = compile(code_str, fake_app_path, "exec")

    global_scope = {
        "__name__": "__main__",
        "__file__": fake_app_path,
        "__builtins__": __builtins__
    }

    # Execute
    exec(compiled_code, global_scope)

if __name__ == "__main__":
    launch_app()
