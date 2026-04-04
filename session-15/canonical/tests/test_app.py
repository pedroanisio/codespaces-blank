import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00"
    b"\xc9\xfe\x92\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class FlaskAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "UPLOAD_DIR": self.root / "uploads",
                "OUTPUT_DIR": self.root / "outputs",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_home_page_renders_upload_form(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Upload an image", response.data)

    def test_upload_processes_image_and_shows_side_by_side_result(self) -> None:
        output_dir = self.root / "outputs"
        processed_path = output_dir / "processed" / "result.png"
        processed_path.parent.mkdir(parents=True, exist_ok=True)
        processed_path.write_bytes(PNG_BYTES)

        with patch("app.process_image") as mocked_process:
            mocked_process.return_value = {
                "processed_image": processed_path.name,
                "processed_relpath": "processed/result.png",
                "json_relpath": "json/result.json",
            }
            response = self.client.post(
                "/upload",
                data={"image": (io.BytesIO(PNG_BYTES), "source.png")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Original image", response.data)
        self.assertIn(b"Regenerated image", response.data)
        self.assertIn(b"/media/uploads/", response.data)
        self.assertIn(b"/media/processed/result.png", response.data)
        mocked_process.assert_called_once()


if __name__ == "__main__":
    unittest.main()
