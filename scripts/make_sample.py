"""Draw a small Thai test page (heading, paragraph, table) as PNG and PDF.

    .venv/bin/python scripts/make_sample.py   ->  samples/thai_table.png, samples/thai_table.pdf
No personal data; for smoke tests only.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = [
    "/System/Library/Fonts/Supplemental/Tahoma.ttf",
    "/System/Library/Fonts/Thonburi.ttc",
    "/Library/Fonts/Tahoma.ttf",
    "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
]


def font(size):
    for path in FONTS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("No Thai font found; edit FONTS in scripts/make_sample.py")


def main():
    out = Path(__file__).resolve().parent.parent / "samples"
    out.mkdir(exist_ok=True)
    w, h = 1654, 2339  # A4 at 200 dpi
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    d.text((w // 2, 160), "บันทึกข้อความ", font=font(64), fill="black", anchor="mm")
    body = font(36)
    d.text((150, 300), "เรื่อง  สรุปการลาของบุคลากร ประจำเดือนตุลาคม ๒๕๖๙", font=body, fill="black")
    d.text((150, 370), "ตามที่หน่วยงานได้รวบรวมข้อมูลการลา จึงขอสรุปไว้ดังตารางต่อไปนี้", font=body, fill="black")

    cols = [150, 300, 800, 1100, 1500]
    rows = [470, 550, 630, 710, 790, 870]
    data = [
        ["ลำดับ", "ประเภทการลา", "จำนวนคน", "จำนวนวัน"],
        ["๑", "ลาป่วย", "๑๒", "๒๕"],
        ["๒", "ลากิจส่วนตัว", "๗", "๙"],
        ["๓", "ลาพักผ่อน", "๑๕", "๔๒"],
        ["", "รวม", "๓๔", "๗๖"],
    ]
    for y in rows:
        d.line((cols[0], y, cols[-1], y), fill="black", width=3)
    for x in cols:
        d.line((x, rows[0], x, rows[-1]), fill="black", width=3)
    for r, row in enumerate(data):
        for c, cell in enumerate(row):
            cx = (cols[c] + cols[c + 1]) // 2
            cy = (rows[r] + rows[r + 1]) // 2
            d.text((cx, cy), cell, font=body, fill="black", anchor="mm")
    d.text((150, 960), "จึงเรียนมาเพื่อโปรดทราบ", font=body, fill="black")

    img.save(out / "thai_table.png")
    img.save(out / "thai_table.pdf", resolution=200)
    print(out / "thai_table.png")
    print(out / "thai_table.pdf")


if __name__ == "__main__":
    main()
