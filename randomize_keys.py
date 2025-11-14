import os
import random

# Read all key files
keys = {}
for f in ['key_1.txt', 'key_3.txt', 'key2_.txt', 'key5.txt']:
    with open(os.path.join('encryption', f), 'r') as file:
        keys[f] = file.read().strip()

# Concatenate all keys
all_keys = ''.join(keys.values())

# Shuffle all characters randomly
chars = list(all_keys)
random.shuffle(chars)
randomized = ''.join(chars)

# Write to ULTIMATE_KEY.md
with open('ULTIMATE_KEY.md', 'w') as f:
    f.write('# Ultimate Randomized Key\n\n')
    f.write(randomized)

print('Fully randomized key created in ULTIMATE_KEY.md')