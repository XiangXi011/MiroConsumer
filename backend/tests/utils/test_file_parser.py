from __future__ import annotations

import base64

from app.utils.file_parser import FileParser


def test_extract_text_describes_uploaded_packaging_image(tmp_path):
    image_path = tmp_path / "舒客酵素亮白牙膏-包装正面.png"
    image_path.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        )
    )

    text = FileParser.extract_text(str(image_path))

    assert "包装/图片素材" in text
    assert "舒客酵素亮白牙膏-包装正面.png" in text
    assert "1x1" in text


def test_extract_text_summarizes_packaging_image_pixels(tmp_path):
    from PIL import Image

    image_path = tmp_path / "舒客酵素亮白牙膏-绿色包装.png"
    Image.new("RGB", (4, 2), (35, 166, 90)).save(image_path)

    text = FileParser.extract_text(str(image_path))

    assert "视觉摘要" in text
    assert "横版包装图" in text
    assert "#23a65a" in text
