#!/usr/bin/env python3
"""
Generate placeholder images for tamagotchi-ui.
Run from the ui/ directory: python generate_placeholders.py
Requires Pillow: pip install Pillow
"""
import os
from PIL import Image, ImageDraw

os.makedirs('static/avatar', exist_ok=True)
os.makedirs('static/backgrounds', exist_ok=True)


def text_center(draw, img_w, img_h, text, fill):
    # Simple centered text with bbox
    bbox = draw.textbbox((0, 0), text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((img_w - tw) // 2, (img_h - th) // 2), text, fill=fill)


# ------------------------------------------------------------------
# Background images (800 x 450, JPEG)
# ------------------------------------------------------------------
BACKGROUNDS = {
    'default':    ((45,  55,  72),  'DEFAULT'),
    'sexual':     ((120, 40,  80),  'SEXUAL'),
    'social':     ((40,  80,  120), 'SOCIAL'),
    'pain':       ((100, 30,  30),  'PAIN'),
    'breathwork': ((30,  100, 80),  'BREATHWORK'),
    'food':       ((100, 80,  30),  'FOOD'),
    'rest':       ((40,  40,  80),  'REST'),
    'sleep':      ((20,  20,  60),  'SLEEP'),
    'drugs':      ((80,  30,  100), 'DRUGS'),
    'medical':    ((30,  80,  100), 'MEDICAL'),
    'life':       ((60,  80,  40),  'LIFE'),
}

for name, (color, label) in BACKGROUNDS.items():
    img = Image.new('RGB', (800, 450), color)
    draw = ImageDraw.Draw(img)
    # Vignette-ish: darker edges
    for i in range(80):
        alpha = int(60 * (1 - i / 80))
        draw.rectangle([i, i, 800 - i, 450 - i],
                       outline=(0, 0, 0, alpha) if False else None)
    text_center(draw, 800, 450, label, (255, 255, 255))
    path = f'static/backgrounds/{name}.jpg'
    img.save(path, 'JPEG', quality=85)
    print(f'  created {path}')


# ------------------------------------------------------------------
# Avatar images (200 x 300, RGBA PNG)
# Each is a simple stick-figure silhouette + expression indicator.
# Replace these with your actual art later.
# ------------------------------------------------------------------
AVATAR_BODY_COLOR = (180, 160, 140, 220)

EXPRESSIONS = {
    'base':     (AVATAR_BODY_COLOR, ''),
    'neutral':  ((160, 140, 120, 230), ':|'),
    'happy':    ((240, 190, 60,  230), ':)'),
    'ecstatic': ((255, 140, 40,  230), ':D'),
    'sad':      ((80,  100, 180, 230), ':('),
    'anxious':  ((210, 70,  70,  230), '>_<'),
    'sleepy':   ((100, 100, 160, 230), '-_-'),
    'blank':    ((120, 120, 120, 180), '...'),
}

for name, (color, label) in EXPRESSIONS.items():
    img = Image.new('RGBA', (200, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Head (circle)
    draw.ellipse([50, 20, 150, 120], fill=color)
    # Body (rounded rectangle)
    draw.rounded_rectangle([65, 125, 135, 240], radius=12, fill=color)
    # Left arm
    draw.rounded_rectangle([30, 130, 65, 155], radius=8, fill=color)
    # Right arm
    draw.rounded_rectangle([135, 130, 170, 155], radius=8, fill=color)
    # Left leg
    draw.rounded_rectangle([68, 240, 95, 290], radius=8, fill=color)
    # Right leg
    draw.rounded_rectangle([105, 240, 132, 290], radius=8, fill=color)

    # Expression label on head
    if label:
        bbox = draw.textbbox((0, 0), label)
        tw = bbox[2] - bbox[0]
        draw.text((100 - tw // 2, 60), label, fill=(255, 255, 255, 220))

    path = f'static/avatar/{name}.png'
    img.save(path, 'PNG')
    print(f'  created {path}')

print('\nDone. Replace these placeholders with your actual artwork.')
