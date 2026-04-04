from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from processor import process_image


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="dev",
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        UPLOAD_DIR=Path("instance/uploads"),
        OUTPUT_DIR=Path("instance/outputs"),
    )
    if config:
        app.config.update(config)

    app.config["UPLOAD_DIR"] = Path(app.config["UPLOAD_DIR"])
    app.config["OUTPUT_DIR"] = Path(app.config["OUTPUT_DIR"])
    app.config["UPLOAD_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        return render_template("index.html", result=None)

    @app.post("/upload")
    def upload():
        file = request.files.get("image")
        if file is None or file.filename == "":
            flash("Choose an image to upload.")
            return redirect(url_for("index"))

        original_name = secure_filename(file.filename)
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            flash("Unsupported file type. Use PNG, JPG, JPEG, WEBP, or BMP.")
            return redirect(url_for("index"))

        image_id = uuid4().hex
        stored_name = f"{image_id}{suffix}"
        upload_path = app.config["UPLOAD_DIR"] / stored_name
        file.save(upload_path)

        try:
            artifacts = process_image(upload_path, app.config["OUTPUT_DIR"], image_id)
        except Exception as exc:
            upload_path.unlink(missing_ok=True)
            flash(f"Image processing failed: {exc}")
            return redirect(url_for("index"))

        result = {
            "original_name": original_name,
            "original_url": url_for("media", kind="uploads", filename=stored_name),
            "processed_url": url_for("media", kind="processed", filename=artifacts["processed_image"]),
            "json_url": url_for("media", kind="json", filename=Path(artifacts["json_relpath"]).name),
        }
        return render_template("index.html", result=result)

    @app.get("/media/<kind>/<path:filename>")
    def media(kind: str, filename: str):
        directories = {
            "uploads": app.config["UPLOAD_DIR"],
            "processed": app.config["OUTPUT_DIR"] / "processed",
            "json": app.config["OUTPUT_DIR"] / "json",
        }
        directory = directories.get(kind)
        if directory is None:
            return redirect(url_for("index"))
        return send_from_directory(directory, filename)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
