import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.db"
STATIC_DIR = BASE_DIR / "static"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


DEFAULT_SITE = {
    "companyName": "公司名称",
    "companyIntro": "在管理页填写公司介绍内容。",
    "contactText": "工作日 9:00-18:00",
    "contactPhone": "",
    "contactEmail": "",
    "contactAddress": "",
    "heroImageUrl": None,
    "promoVideoUrl": None,
}


def init_db() -> None:
    ensure_dirs()
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS site_config (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              data TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              cover_url TEXT NULL,
              media_type TEXT NOT NULL CHECK (media_type IN ('image','video')),
              media_url TEXT NULL,
              sort_order INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              phone TEXT NOT NULL,
              wechat TEXT NULL,
              email TEXT NULL,
              message TEXT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        cur = conn.execute("SELECT data FROM site_config WHERE id = 1;")
        row = cur.fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO site_config (id, data, updated_at) VALUES (1, ?, ?);",
                (json.dumps(DEFAULT_SITE, ensure_ascii=False), utc_now_iso()),
            )


def load_site(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT data FROM site_config WHERE id = 1;").fetchone()
    if not row:
        return dict(DEFAULT_SITE)
    try:
        data = json.loads(row["data"])
        if not isinstance(data, dict):
            return dict(DEFAULT_SITE)
        merged = dict(DEFAULT_SITE)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_SITE)


def save_site(conn: sqlite3.Connection, data: dict) -> None:
    merged = dict(DEFAULT_SITE)
    merged.update(data or {})
    conn.execute(
        "UPDATE site_config SET data = ?, updated_at = ? WHERE id = 1;",
        (json.dumps(merged, ensure_ascii=False), utc_now_iso()),
    )


def product_row_to_dict(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "title": r["title"],
        "description": r["description"],
        "coverUrl": r["cover_url"],
        "mediaType": r["media_type"],
        "mediaUrl": r["media_url"],
        "sortOrder": r["sort_order"],
    }


def allowed_file(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".mp4",
        ".webm",
        ".mov",
        ".m4v",
    }


def guess_media_type(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext in {".mp4", ".webm", ".mov", ".m4v"}:
        return "video"
    return "image"


app = Flask(__name__)
CORS(app)

@app.get("/")
@app.get("/<path:path>")
def spa(path: str = ""):
    # 只处理前端静态资源与 SPA 路由回退，避免影响 /api 与 /media
    if request.path.startswith("/api") or request.path.startswith("/media"):
        return jsonify({"error": "not found"}), 404

    index = STATIC_DIR / "index.html"
    if not index.exists():
        return (
            jsonify(
                {
                    "error": "frontend not built",
                    "hint": "run: cd frontend && npm run build",
                }
            ),
            503,
        )

    candidate = (STATIC_DIR / path).resolve()
    if path and str(candidate).startswith(str(STATIC_DIR.resolve())) and candidate.is_file():
        return send_from_directory(STATIC_DIR, path)

    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/media/<path:filename>")
def media(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get("/api/public/site")
def api_public_site():
    with get_db() as conn:
        return jsonify(load_site(conn))


@app.get("/api/public/products")
def api_public_products():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY sort_order ASC, id ASC;"
        ).fetchall()
        return jsonify([product_row_to_dict(r) for r in rows])


@app.post("/api/public/leads")
def api_public_leads_create():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    phone = str(payload.get("phone") or "").strip()
    wechat = payload.get("wechat")
    email = payload.get("email")
    message = payload.get("message")

    if not name or not phone:
        return jsonify({"error": "name/phone required"}), 400

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO leads (name, phone, wechat, email, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                name,
                phone,
                (str(wechat).strip() if wechat else None),
                (str(email).strip() if email else None),
                (str(message).strip() if message else None),
                utc_now_iso(),
            ),
        )
    return jsonify({"ok": True})


@app.get("/api/admin/site")
def api_admin_site_get():
    with get_db() as conn:
        return jsonify(load_site(conn))


@app.put("/api/admin/site")
def api_admin_site_put():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid payload"}), 400
    with get_db() as conn:
        save_site(conn, payload)
    return jsonify({"ok": True})


@app.get("/api/admin/products")
def api_admin_products_get():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY sort_order ASC, id ASC;"
        ).fetchall()
        return jsonify([product_row_to_dict(r) for r in rows])


@app.post("/api/admin/products")
def api_admin_products_upsert():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid payload"}), 400

    pid = payload.get("id")
    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "")
    cover_url = payload.get("coverUrl")
    media_type = payload.get("mediaType") or "image"
    media_url = payload.get("mediaUrl")
    sort_order = payload.get("sortOrder")

    if not title:
        return jsonify({"error": "title required"}), 400
    if media_type not in {"image", "video"}:
        return jsonify({"error": "invalid mediaType"}), 400

    try:
        sort_order_int = int(sort_order or 0)
    except Exception:
        sort_order_int = 0

    now = utc_now_iso()
    with get_db() as conn:
        if isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit()):
            pid_int = int(pid)
            conn.execute(
                """
                UPDATE products
                SET title = ?, description = ?, cover_url = ?, media_type = ?, media_url = ?, sort_order = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    description,
                    (str(cover_url).strip() if cover_url else None),
                    media_type,
                    (str(media_url).strip() if media_url else None),
                    sort_order_int,
                    now,
                    pid_int,
                ),
            )
            row = conn.execute("SELECT * FROM products WHERE id = ?;", (pid_int,)).fetchone()
            if not row:
                return jsonify({"error": "not found"}), 404
            return jsonify(product_row_to_dict(row))

        cur = conn.execute(
            """
            INSERT INTO products (title, description, cover_url, media_type, media_url, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                title,
                description,
                (str(cover_url).strip() if cover_url else None),
                media_type,
                (str(media_url).strip() if media_url else None),
                sort_order_int,
                now,
                now,
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM products WHERE id = ?;", (new_id,)).fetchone()
        return jsonify(product_row_to_dict(row))


@app.delete("/api/admin/products/<int:pid>")
def api_admin_products_delete(pid: int):
    with get_db() as conn:
        conn.execute("DELETE FROM products WHERE id = ?;", (pid,))
    return jsonify({"ok": True})


@app.post("/api/admin/upload")
def api_admin_upload():
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "file required"}), 400

    if not allowed_file(f.filename):
        return jsonify({"error": "file type not allowed"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    safe_name = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex}{ext}"
    ensure_dirs()
    save_path = UPLOAD_DIR / safe_name
    f.save(save_path)

    media_type = guess_media_type(f.filename)
    base = request.host_url.rstrip("/")
    return jsonify({"url": f"{base}/media/{safe_name}", "mediaType": media_type})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)

