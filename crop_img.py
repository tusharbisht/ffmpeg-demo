from PIL import Image
img = Image.open("frames/frame_000080.png")  # your file
print("size:", img.size)
c = (260, 160, 1040, 250)  # tweak here
img.crop(c).save("tmp_crop.png")