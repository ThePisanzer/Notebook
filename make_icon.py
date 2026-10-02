from PIL import Image, ImageDraw, ImageFont

SIZE = 512
BG_COLOR = (80, 80, 80, 255)
BORDER_COLOR = (255, 255, 255, 255)
TEXT_COLOR = (255, 255, 255, 255)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

margin = 40
draw.rounded_rectangle(
    [margin, margin, SIZE - margin, SIZE - margin],
    radius=70,
    fill=BG_COLOR,
    outline=BORDER_COLOR,
    width=12
)

font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 300)
text = "N"
bbox = draw.textbbox((0, 0), text, font=font)
w = bbox[2] - bbox[0]
h = bbox[3] - bbox[1]
draw.text(
    ((SIZE - w) / 2 - bbox[0], (SIZE - h) / 2 - bbox[1]),
    text,
    font=font,
    fill=TEXT_COLOR
)

img.save("icon.png")

sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save("icon.ico", format="ICO", sizes=sizes)

print("生成完成：icon.png 和 icon.ico")
