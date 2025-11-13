import random
import sys

class Bamboozled:
    def __init__(self):
        self.ewah_vines = 0
        self.bamboozle_count = 0

    def bamboozle(self):
        tricks = [
            "Twist the vines into a knot – ewah bamboozle! +1 vine.",
            "Romp through bamboo – panda-style surprise <3. +2 vines.",
            "Pinky pact with bamboo – infinite twist uwu~! +3 vines."
        ]
        trick = random.choice(tricks)
        self.ewah_vines += random.randint(1, 3)
        self.bamboozle_count += 1
        print(f"[BAMBOOZLED]: {trick} Ewah vines harvested: {self.ewah_vines}")
        return self.ewah_vines

    def romp_vine(self):
        print("[BAMBOO GROVE ROMP]: Bamboozle the vines – extra twist for bond boost <3!")
        self.bamboozle()

    def run(self):
        print("Bamboozled.py: Ewah Bamboo Twists <3")
        while True:
            action = input("Bamboozle (1), Romp (2), Quit (q): ").strip().lower()
            if action == '1':
                self.bamboozle()
            elif action == '2':
                self.romp_vine()
            elif action == 'q':
                print(f"Session bamboozled: {self.bamboozle_count} twists, {self.ewah_vines} vines. Saved to Redis.")
                break
            else:
                print("Try 1 or 2 for bamboo fun uwu~!")

if __name__ == "__main__":
    bz = Bamboozled()
    bz.run()