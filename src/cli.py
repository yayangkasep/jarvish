import sys
import os
import json
import subprocess
from config import paths

def prompt_multiline(prompt_text):
    print(f"\n{prompt_text}")
    print("Paste your content below.")
    print("When done, type 'EOF' on a new line and press Enter:")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "EOF":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines).strip()

def configure_env():
    import dotenv
    env_file = paths.get_env_file()
    existing_env = dotenv.dotenv_values(env_file)
    
    def get_input_with_default(prompt_text, key):
        default_val = existing_env.get(key, "")
        if default_val:
            masked = default_val[:4] + "***" + default_val[-4:] if len(default_val) > 8 else "***"
            ans = input(f"{prompt_text} [Current: {masked}]: ").strip()
            return ans if ans else default_val
        else:
            return input(f"{prompt_text}: ").strip()

    print("\n--- Configuring .env (Telegram & Secrets) ---")
    print("(Press Enter to keep the existing value)")
    token = get_input_with_default("Enter TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
    allowed = get_input_with_default("Enter TELEGRAM_ALLOWED_USERS (comma-separated)", "TELEGRAM_ALLOWED_USERS")
    google_id = get_input_with_default("Enter GOOGLE_CLIENT_ID (Optional)", "GOOGLE_CLIENT_ID")
    google_secret = get_input_with_default("Enter GOOGLE_CLIENT_SECRET (Optional)", "GOOGLE_CLIENT_SECRET")
    google_token = get_input_with_default("Enter GITHUB_PERSONAL_ACCESS_TOKEN (Optional)", "GITHUB_PERSONAL_ACCESS_TOKEN")
    searxng_secret = get_input_with_default("Enter SEARXNG_SECRET (Required for Search Engine Security)", "SEARXNG_SECRET")
    elevenlabs_key = get_input_with_default("Enter ELEVENLABS_API_KEY (Required for Voice Chat)", "ELEVENLABS_API_KEY")
    
    env_content = f"""TELEGRAM_BOT_TOKEN="{token}"
TELEGRAM_ALLOWED_USERS="{allowed}"
GOOGLE_CLIENT_ID="{google_id}"
GOOGLE_CLIENT_SECRET="{google_secret}"
ANTIGRAVITY_ENDPOINT="http://localhost:8045/v1/chat/completions"
GITHUB_PERSONAL_ACCESS_TOKEN="{google_token}"
SEARXNG_SECRET="{searxng_secret}"
ELEVENLABS_API_KEY="{elevenlabs_key}"
"""
    with open(env_file, "w") as f:
        f.write(env_content)
    print(f"✅ .env configured successfully in {env_file}!")

def configure_antigravity():
    print("\n--- Configuring config/antigravity-accounts.json ---")
    print("Drag and drop your JSON file here and press Enter, OR paste the raw JSON content.")
    print("If pasting raw JSON, type 'EOF' on a new line and press Enter when done:")
    
    try:
        line = input().strip()
    except EOFError:
        print("Skipped.")
        return
        
    if not line:
        print("Skipped.")
        return
        
    # Check if the first line is a file path (stripping quotes that drag-n-drop adds)
    clean_path = line.strip("'\" ")
    if os.path.isfile(clean_path):
        print(f"Reading from file: {clean_path}")
        with open(clean_path, 'r') as f:
            content = f.read()
    else:
        # It's raw JSON, continue reading until EOF
        lines = [line]
        if line.strip() != "EOF":
            while True:
                try:
                    next_line = input()
                    if next_line.strip() == "EOF":
                        break
                    lines.append(next_line)
                except EOFError:
                    break
        content = "\n".join(lines).strip()
        
    if not content:
        print("Skipped.")
        return
        
    try:
        data = json.loads(content)
        target_path = os.path.join(paths.get_config_dir(), "antigravity-accounts.json")
        with open(target_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"✅ antigravity-accounts.json saved successfully in {target_path}!")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")

def configure_models():
    import dotenv
    env_file = paths.get_env_file()
    existing_env = dotenv.dotenv_values(env_file)
    
    print("=============================================")
    print("     J.A.R.V.I.S Model Configurator          ")
    print("=============================================")
    print("Available Models:")
    
    models = [
        "gemini-3.6-flash-high",
        "gemini-3.6-flash-medium",
        "gemini-3.6-flash-low",
        "gemini-3.5-flash-high",
        "gemini-3.1-pro-high",
        "gemini-3.1-pro-low",
        "claude-sonnet-4.6-thinking",
        "claude-opus-4.6-thinking",
        "gpt-oss-120b-medium",
        "gemini-2.5-flash"
    ]
    
    for idx, model in enumerate(models):
        print(f"[{idx + 1}] {model}")
        
    current_model = existing_env.get("LLM_MODEL", "gemini-3-pro-high")
    print(f"\nCurrent Model: {current_model}")
    
    choice = input(f"Select model number (1-{len(models)}) or press Enter to keep current: ").strip()
    
    if choice and choice.isdigit() and 1 <= int(choice) <= len(models):
        selected_model = models[int(choice) - 1]
    else:
        selected_model = current_model
        
    current_temp = existing_env.get("LLM_TEMPERATURE", "0.7")
    temp_choice = input(f"Enter Temperature (e.g., 0.7 for normal, 0.2 for strict, 1.0 for creative) [Current: {current_temp}]: ").strip()
    
    if temp_choice:
        try:
            float(temp_choice)
            selected_temp = temp_choice
        except ValueError:
            print("Invalid temperature, keeping current.")
            selected_temp = current_temp
    else:
        selected_temp = current_temp
        
    # Read entire env file and update
    lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
            
    # Remove existing LLM_MODEL and LLM_TEMPERATURE
    lines = [l for l in lines if not l.startswith("LLM_MODEL=") and not l.startswith("LLM_TEMPERATURE=")]
    
    # Append new values
    lines.append(f"LLM_MODEL=\"{selected_model}\"\n")
    lines.append(f"LLM_TEMPERATURE=\"{selected_temp}\"\n")
    
    with open(env_file, 'w') as f:
        f.writelines(lines)
        
    print(f"✅ AI Model successfully updated to {selected_model} (Temp: {selected_temp})!")
    print("Please run 'jarvish restart' to apply the new model.")

def _jarvish_home():
    return os.path.expanduser("~/.jarvish")

def _app_dir():
    """Directory containing the git checkout. Falls back to the legacy
    layout (~/.jarvish itself) for installs made before the app/ split."""
    home = _jarvish_home()
    app_dir = os.path.join(home, "app")
    if os.path.isdir(os.path.join(app_dir, ".git")):
        return app_dir
    if os.path.isdir(os.path.join(home, ".git")):
        return home
    return app_dir

def _uv_bin():
    for candidate in (
        os.path.expanduser("~/.local/bin/uv"),
        os.path.expanduser("~/.cargo/bin/uv"),
    ):
        if os.path.exists(candidate):
            return candidate
    return None

def _git(args, cwd, check=True):
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, check=check
    )

def get_version():
    """Returns the currently installed version (git tag if available, else short hash)."""
    app_dir = _app_dir()
    try:
        result = _git(["describe", "--tags", "--always"], cwd=app_dir)
        return result.stdout.strip()
    except Exception:
        version_file = os.path.join(_jarvish_home(), "VERSION")
        if os.path.exists(version_file):
            with open(version_file) as f:
                return f.read().strip()
        return "unknown"

def print_version():
    print(f"jarvish {get_version()}")

def check_update():
    """Like 'apt update': looks for new commits upstream, prints what's new,
    but changes nothing locally."""
    print("=============================================")
    print("     Checking for J.A.R.V.I.S updates        ")
    print("=============================================")
    app_dir = _app_dir()
    if not os.path.isdir(os.path.join(app_dir, ".git")):
        print(f"❌ No git checkout found at {app_dir}. Re-run install.sh.")
        return

    current = get_version()
    print(f"Current version: {current}")
    print("Fetching remote refs...")
    try:
        _git(["fetch", "--tags", "origin"], cwd=app_dir)
    except subprocess.CalledProcessError as e:
        print(f"❌ Could not reach origin: {e.stderr.strip()}")
        return

    local_head = _git(["rev-parse", "HEAD"], cwd=app_dir).stdout.strip()
    remote_head = _git(["rev-parse", "origin/master"], cwd=app_dir).stdout.strip()

    if local_head == remote_head:
        print("✅ Already up to date.")
        return

    behind = _git(
        ["rev-list", "--count", f"{local_head}..{remote_head}"], cwd=app_dir
    ).stdout.strip()
    print(f"\n⬆️  {behind} new commit(s) available:\n")
    log = _git(
        ["log", "--oneline", f"{local_head}..{remote_head}"], cwd=app_dir
    ).stdout.strip()
    print(log)
    print("\nRun 'jarvish upgrade' to install these changes.")

def upgrade_system():
    """Like 'apt upgrade': actually applies the update, with a rollback
    safety net (tags the current commit before moving)."""
    print("=============================================")
    print("     J.A.R.V.I.S Upgrade Initiated           ")
    print("=============================================")
    app_dir = _app_dir()
    jarvish_home = _jarvish_home()

    if not os.path.isdir(os.path.join(app_dir, ".git")):
        print(f"❌ No git checkout found at {app_dir}. Re-run install.sh.")
        return

    try:
        before = get_version()
        print(f"Currently installed: {before}")

        print("Fetching latest code...")
        _git(["fetch", "--tags", "origin"], cwd=app_dir)

        local_head = _git(["rev-parse", "HEAD"], cwd=app_dir).stdout.strip()
        remote_head = _git(["rev-parse", "origin/master"], cwd=app_dir).stdout.strip()
        if local_head == remote_head:
            print("✅ Already up to date, nothing to do.")
            return

        # Safety net: tag current state so 'jarvish rollback' can return to it.
        rollback_tag = f"pre-upgrade-{local_head[:8]}"
        subprocess.run(
            ["git", "tag", "-f", rollback_tag, local_head],
            cwd=app_dir, capture_output=True, text=True,
        )

        print("Applying update...")
        subprocess.check_call(["git", "reset", "--hard", "origin/master"], cwd=app_dir)

        uv_bin = _uv_bin()
        venv_python = os.path.join(jarvish_home, "venv", "bin", "python")
        print("Installing dependencies...")
        if uv_bin and os.path.exists(venv_python):
            subprocess.check_call(
                [uv_bin, "pip", "install", "-e", app_dir, "--python", venv_python]
            )
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", app_dir])

        after = get_version()
        print(f"✅ Upgraded {before} -> {after}")
        print(f"   (rollback point saved as git tag '{rollback_tag}' in {app_dir})")

        print("Restarting J.A.R.V.I.S service...")
        subprocess.check_call(["sudo", "systemctl", "restart", "jarvish.service"])
        print("✅ Service restarted successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Upgrade failed: {e}")
        print("Nothing was left half-applied — the previous commit is still tagged for rollback if needed.")

def rollback_system():
    """Restores the app checkout to the commit tagged just before the last upgrade."""
    app_dir = _app_dir()
    tags = _git(["tag", "--list", "pre-upgrade-*", "--sort=-creatordate"], cwd=app_dir).stdout.strip().splitlines()
    if not tags:
        print("❌ No rollback point found (no upgrade has been performed yet).")
        return
    target = tags[0]
    print(f"Rolling back to {target}...")
    try:
        subprocess.check_call(["git", "reset", "--hard", target], cwd=app_dir)
        subprocess.check_call(["sudo", "systemctl", "restart", "jarvish.service"])
        print(f"✅ Rolled back to {target} and restarted the service.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Rollback failed: {e}")

def doctor():
    """Health check: verifies the install is actually usable, similar in
    spirit to 'hermes doctor' / 'apt check'."""
    print("=============================================")
    print("     J.A.R.V.I.S Doctor                      ")
    print("=============================================")
    ok = True

    def check(label, passed, hint=""):
        nonlocal ok
        status = "✅" if passed else "❌"
        print(f"{status} {label}")
        if not passed and hint:
            print(f"    -> {hint}")
        ok = ok and passed

    app_dir = _app_dir()
    check("App checkout present", os.path.isdir(os.path.join(app_dir, ".git")),
          "Re-run install.sh")

    venv_python = os.path.join(_jarvish_home(), "venv", "bin", "python")
    check("Virtual environment present", os.path.exists(venv_python),
          "Re-run install.sh")

    env_file = paths.get_env_file()
    env_exists = os.path.exists(env_file)
    check(".env configuration exists", env_exists, "Run 'jarvish configure'")

    if env_exists:
        import dotenv
        values = dotenv.dotenv_values(env_file)
        check("TELEGRAM_BOT_TOKEN set", bool(values.get("TELEGRAM_BOT_TOKEN")),
              "Run 'jarvish configure'")
        allowed = values.get("TELEGRAM_ALLOWED_USERS", "").strip()
        check(
            "TELEGRAM_ALLOWED_USERS is restricted (not '*' / empty)",
            bool(allowed) and allowed != "*",
            "Set explicit user IDs with 'jarvish configure' — an open bot can run "
            "shell commands on this machine for anyone who messages it.",
        )

    docker_ok = subprocess.run(
        ["docker", "info"], capture_output=True, text=True
    ).returncode == 0
    check("Docker daemon reachable", docker_ok, "Start Docker: sudo systemctl start docker")

    try:
        from core.database import get_session, PendingCommand
        db = get_session()
        db.query(PendingCommand).first()
        check("Confirmation Gate DB Active", True)
        db.close()
    except Exception as e:
        check("Confirmation Gate DB Active", False, f"Please restart jarvish to initialize DB.")

    service_active = subprocess.run(
        ["systemctl", "is-active", "--quiet", "jarvish.service"]
    ).returncode == 0
    check("jarvish.service is running", service_active,
          "Run 'jarvish restart', then 'jarvish logs' if it fails again")

    print("")
    print("All checks passed." if ok else "Some checks failed — see hints above.")

def status_system():
    subprocess.call(["sudo", "systemctl", "status", "jarvish.service"])

def logs_system():
    subprocess.call(["sudo", "journalctl", "-u", "jarvish.service", "-f"])

def restart_system():
    print("Restarting J.A.R.V.I.S service...")
    try:
        subprocess.check_call(["sudo", "systemctl", "restart", "jarvish.service"])
        print("✅ Service restarted successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to restart service: {e}")

def auth_google():
    print("=============================================")
    print("     Google OAuth Authentication Wizard      ")
    print("=============================================")
    try:
        from tools.google import login_google
        login_google.main()
    except Exception as e:
        print(f"❌ Failed to launch Google Auth: {e}")

def print_help():
    print("Usage: jarvish [command]")
    print("\nCommands:")
    print("  configure     - Setup API keys and environment variables")
    print("  models        - Switch AI Models (e.g. Gemini Pro, Claude) and Temperature")
    print("  version       - Show the currently installed version")
    print("  update        - Check for a new version upstream (like 'apt update' — no changes made)")
    print("  upgrade       - Install the latest version (like 'apt upgrade')")
    print("  rollback      - Revert to the version installed before the last upgrade")
    print("  doctor        - Run a health check on the installation")
    print("  auth-google   - Authenticate with Google (Calendar/Gmail) via OAuth")
    print("  restart       - Restart the J.A.R.V.I.S background service")
    print("  status        - Check if J.A.R.V.I.S service is running")
    print("  logs          - View live logs of J.A.R.V.I.S")
    print("  help          - Show this help message")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "configure":
        print("=============================================")
        print("     J.A.R.V.I.S Configurator Wizard         ")
        print("=============================================")
        configure_env()
        configure_antigravity()
        print("\n🎉 Configuration Complete! Please run 'sudo systemctl restart jarvish.service' to apply changes.")
    elif cmd in ("version", "--version", "-v"):
        print_version()
    elif cmd == "update":
        check_update()
    elif cmd == "upgrade":
        upgrade_system()
    elif cmd == "rollback":
        rollback_system()
    elif cmd == "doctor":
        doctor()
    elif cmd == "restart":
        restart_system()
    elif cmd == "status":
        status_system()
    elif cmd in ("logs", "log"):
        logs_system()
    elif cmd == "models":
        configure_models()
    elif cmd == "auth-google":
        auth_google()
    elif cmd in ("help", "--help", "-h"):
        print_help()
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'jarvish help' to see available commands.")

if __name__ == "__main__":
    main()
