import socket
import os
import re

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def update_file(file_path, pattern, replacement):
    if not os.path.exists(file_path):
        print(f"Warning: File not found: {file_path}")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        if content != new_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {file_path}")
        else:
            print(f"No changes needed for {file_path}")

    except Exception as e:
        print(f"Error updating {file_path}: {e}")


def main():
    ip = get_local_ip()
    print("Detected Local IP:", ip)

    # -----------------------------
    # WEBSITE CONFIG (config.js)
    # -----------------------------
    website_config = os.path.join("website", "src", "config.js")

    update_file(
        website_config,
        r"export\s+const\s+API_BASE_URL\s*=.*?;",
        f"export const API_BASE_URL = `http://{ip}:8000`;"
    )


    mobile_config = os.path.join("mobile-app", "App.js")

    update_file(
        mobile_config,
        r"const\s+WEBSITE_URL\s*=.*?;",
        f"const WEBSITE_URL = 'http://{ip}:5173/';"
    )


if __name__ == "__main__":
    main()
