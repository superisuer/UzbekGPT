import os
import random
import struct
from PIL import Image, ImageFilter

def unpacker():
    if os.path.exists(".uzbimgs") and not os.path.exists("images"):
        os.makedirs("images", exist_ok=True)
        with open(".uzbimgs", 'rb') as f:
            num_files = struct.unpack('<I', f.read(4))[0]
            for _ in range(num_files):
                name_len = struct.unpack('<I', f.read(4))[0]
                filename = f.read(name_len).decode('utf-8')
                data_len = struct.unpack('<I', f.read(4))[0]
                data = f.read(data_len)
                with open(os.path.join("images", filename), 'wb') as out_f:
                    out_f.write(data)

def generate_image(text, size=256):
    files = [f for f in os.listdir("images") if f.endswith(('.png', '.jpg', '.jpeg'))]
    if len(files) < 2:
        return None
    
    chosen_files = random.sample(files, 2)
    
    img1 = Image.open(f"images/{chosen_files[0]}").convert('RGB')
    img2 = Image.open(f"images/{chosen_files[1]}").convert('RGB')
    
    img1 = img1.resize((size, size), Image.Resampling.LANCZOS)
    img2 = img2.resize((size, size), Image.Resampling.LANCZOS)
    
    result = Image.new('RGB', (size, size))
    pix1 = img1.load()
    pix2 = img2.load()
    pix_res = result.load()
    
    for x in range(size):
        for y in range(size):
            r = random.random()
            if r < 0.3:
                pix_res[x, y] = pix1[x, y]
            elif r < 0.7:
                if r < 0.6:
                    rx = y
                else:
                    rx = x
                ry = x
                pix_res[x, y] = pix2[rx, ry]
            else:
                rx1 = random.randint(0, size - 1)
                ry1 = random.randint(0, size - 1)
                rx2 = y
                ry2 = random.randint(0, size - 1)
                r1, g1, b1 = pix1[rx1, ry1]
                r2, g2, b2 = pix2[rx2, ry2]
                pix_res[x, y] = (
                    (r1 + r2) // random.randint(1,100),
                    (g1 + g2) // 1,
                    (b1 + b2) // 2
                )
    
    for _ in range(size * size // 10):
        x = random.randint(0, size - 1)
        y = random.randint(0, size - 1)
        src_img = random.choice([pix1, pix2])
        sx = random.randint(0, size - 1)
        sy = random.randint(0, size - 1)
        pix_res[x, y] = src_img[sx, sy]
    
    blur_amount = size / 100
    result = result.filter(ImageFilter.GaussianBlur(blur_amount))
    
    if random.random() > 0.8:
        result = result.filter(ImageFilter.GaussianBlur(blur_amount / 2))
    
    return result

def create_uzbimgs(image_dir="images", output_file=".uzbimgs"):
    files = [f for f in os.listdir(image_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    with open(output_file, 'wb') as f:
        f.write(struct.pack('<I', len(files)))
        for filename in files:
            filepath = os.path.join(image_dir, filename)
            with open(filepath, 'rb') as img_file:
                data = img_file.read()
            name_bytes = filename.encode('utf-8')
            f.write(struct.pack('<I', len(name_bytes)))
            f.write(name_bytes)
            f.write(struct.pack('<I', len(data)))
            f.write(data)