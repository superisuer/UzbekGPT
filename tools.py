import uzbekimg

print("free tool for uzbekimg!!!!!!!!!")
print("1 - pack ./images/ to .uzbimgs")
print("2 - unpack .uzbimgs to ./images/")
hui = input(": ")
if hui == "1":
    uzbekimg.create_uzbimgs()
elif hui == "2":
    uzbekimg.unpacker()