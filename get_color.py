from PIL import Image
import collections

def get_dominant_color(image_path):
    try:
        img = Image.open(image_path)
        img = img.resize((150, 150))
        img = img.convert("RGB")
        colors = img.getcolors(150 * 150)
        ordered = sorted(colors, key=lambda x: x[0], reverse=True)
        # simplistic dominant color
        most_frequent = ordered[0][1]
        return '#{:02x}{:02x}{:02x}'.format(most_frequent[0], most_frequent[1], most_frequent[2]).upper()
    except Exception as e:
        return str(e)

path = "/Users/souluk/.gemini/antigravity/brain/db55d779-1b33-4ccd-a9a0-555faf4dca2e/uploaded_media_1770269123297.png"
print(get_dominant_color(path))
