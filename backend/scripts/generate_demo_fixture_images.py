"""Generate project-owned, privacy-safe A/B/C demo product screenshot fixtures.

The files are deterministic test artwork, not photographs, user uploads, or
copies of historical assets.  This script is intentionally not part of pytest.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2] / "test-fixtures" / "demo-images"
CASES = (
    ("candidate-a-qingxiang-1.png", "CANDIDATE A / 1", "QINGXIANG TIEGUANYIN", "Origin: Anxi | Clear aroma | 250g", (40, 112, 84)),
    ("candidate-a-qingxiang-2.png", "CANDIDATE A / 2", "QINGXIANG TIEGUANYIN", "Spring tea | Light roast | Detail card", (46, 132, 98)),
    ("candidate-b-nongxiang-1.png", "CANDIDATE B / 1", "NONGXIANG TIEGUANYIN", "Roast: unknown | Rich style | 250g", (126, 70, 42)),
    ("candidate-b-nongxiang-2.png", "CANDIDATE B / 2", "NONGXIANG TIEGUANYIN", "Batch detail | Roast not stated", (144, 86, 52)),
    ("candidate-c-marketing-heavy-1.png", "CANDIDATE C / 1", "PREMIUM TIEGUANYIN", "Marketing claims; core details absent", (111, 80, 30)),
    ("candidate-c-marketing-heavy-2.png", "CANDIDATE C / 2", "PREMIUM TIEGUANYIN", "Luxury claim | Missing harvest and roast", (130, 95, 38)),
)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=24)
    title = ImageFont.load_default(size=38)
    for filename, label, product, detail, accent in CASES:
        image = Image.new("RGB", (960, 640), (248, 245, 235))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((48, 48, 912, 592), radius=28, fill=(255, 255, 255), outline=accent, width=8)
        draw.rounded_rectangle((92, 104, 868, 178), radius=14, fill=accent)
        draw.text((120, 126), label, font=font, fill=(255, 255, 255))
        draw.ellipse((120, 230, 310, 420), fill=(90, 135, 72), outline=accent, width=5)
        draw.text((360, 238), product, font=title, fill=(45, 45, 38))
        draw.text((360, 320), detail, font=font, fill=(70, 70, 62))
        draw.text((360, 392), "PROJECT-OWNED DEMO FIXTURE", font=font, fill=accent)
        image.save(ROOT / filename, format="PNG", optimize=True)


if __name__ == "__main__":
    main()
