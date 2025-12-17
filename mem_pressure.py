import time

chunks = []
MB = 100
for i in range(40):  # ~2 GB
    chunks.append(bytearray(MB * 1024 * 1024))
    time.sleep(0.5)
print('allocated', len(chunks) * MB, 'MB')
time.sleep(300)
