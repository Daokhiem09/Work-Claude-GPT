import os
import json
import urllib.request
import urllib.error
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=os.environ.get("RENDER") == "true", SESSION_COOKIE_SAMESITE="Lax")

# Cấu hình kết nối tới Cloudflare Worker D1
CLOUDFLARE_WORKER_URL = "https://quang-khiem-flow-license.quang-khiem-flow-license-server.workers.dev"
ADMIN_API_TOKEN = os.environ["ADMIN_API_TOKEN"]

# Mật khẩu đăng nhập quản trị khi vào từ điện thoại/web ngoài
# Bạn có thể đổi mật khẩu này theo ý muốn
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def check_auth():
    return session.get("logged_in") is True


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        pwd = request.form.get("password", "").strip()
        if pwd == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin_home"))
        else:
            error = "Mật khẩu quản trị không chính xác!"
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Đăng Nhập Quản Trị · MASTER FLOW</title>
  <style>
    body {{ background: #0b111e; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
    .card {{ background: #131b2e; border: 1px solid #243456; border-radius: 14px; padding: 32px; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: center; }}
    h1 {{ font-size: 20px; margin-bottom: 8px; }}
    p {{ color: #8b9bb4; font-size: 14px; margin-bottom: 24px; }}
    input {{ width: 100%; box-sizing: border-box; padding: 12px 14px; border-radius: 8px; border: 1px solid #243456; background: #091325; color: #fff; font-size: 15px; margin-bottom: 16px; outline: none; }}
    input:focus {{ border-color: #3b82f6; }}
    button {{ width: 100%; padding: 14px; border: none; border-radius: 8px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: #fff; font-size: 16px; font-weight: 700; cursor: pointer; }}
    button:hover {{ opacity: 0.9; }}
    .err {{ color: #ef4444; font-size: 14px; margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>⚡ MASTER FLOW</h1>
    <p>Đăng nhập quản lý bản quyền & cấp key</p>
    {"<div class='err'>" + error + "</div>" if error else ""}
    <form method="POST">
      <input type="password" name="password" placeholder="Nhập mật khẩu quản trị" required autofocus>
      <button type="submit">ĐĂNG NHẬP</button>
    </form>
  </div>
</body>
</html>"""


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@app.route("/admin")
def admin_home():
    if not check_auth():
        return redirect(url_for("login"))
    return render_template("admin_panel.html")


@app.route("/api/v1/admin/<path:subpath>", methods=["GET", "POST", "PATCH", "DELETE"])
def proxy_api(subpath):
    if not check_auth():
        return jsonify({"ok": False, "error": {"code": "UNAUTHORIZED", "message": "Vui lòng đăng nhập"}}), 401

    target_url = f"{CLOUDFLARE_WORKER_URL}/api/v1/admin/{subpath}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    body_bytes = request.get_data() if request.method in ["POST", "PATCH", "PUT"] else None

    req = urllib.request.Request(
        target_url,
        data=body_bytes,
        method=request.method,
        headers={
            "Authorization": f"Bearer {ADMIN_API_TOKEN}",
            "User-Agent": "QuangKhiemFlow-LicenseAdmin/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            return data, resp.status, {"Content-Type": "application/json; charset=utf-8"}
    except urllib.error.HTTPError as e:
        data = e.read()
        return data, e.code, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as e:
        return jsonify({"ok": False, "error": {"code": "GATEWAY_ERROR", "message": str(e)}}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8890))
    print(f"Server started on http://127.0.0.1:{port}/")
    app.run(host="0.0.0.0", port=port, debug=False)
