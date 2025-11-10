#!/usr/bin/env python3
"""
Season Haiku Generator - Self-generated script for Grokputer.
Generates one haiku per season (spring, summer, autumn, winter).
"""

import random

seasons = ["spring", "summer", "autumn", "winter"]

# Haiku structure: 5-7-5 syllables, simple templates for creativity
haiku_templates = {
    "spring": [
        ["Cherry blooms", "Awake from sleep", "New life stirs"],
        ["Rain soft falls", "Buds unfold green", "Birds return"],
        ["Flowers dance", "Winds gentle blow", "Hope renews"]
    ],
    "summer": [
        ["Sun beats down", "Waves crash on shore", "Ice cream melts"],
        ["Barbecues", "Lazy days long", "Fireflies glow"],
        ["Thunderstorms", "Cool evening breeze", "Stars above"]
    ],
    "autumn": [
        ["Leaves turn red", "Harvest moon rises", "Cool air comes"],
        ["Pumpkin spice", "Sweaters and scarves", "Nights grow long"],
        ["Falling leaves", "Crisp morning frost", "Change whispers"]
    ],
    "winter": [
        ["Snowflakes fall", "World wrapped in white", "Silent night"],
        ["Fireplace warm", "Hot cocoa sips", "Holidays near"],
        ["Icicles hang", "Breath clouds the air", "Rest in peace"]
    ]
}

def generate_haiku(season):
    """Generate a random haiku for the given season."""
    if season not in seasons:
        return f"Invalid season: {season}"
    
    templates = haiku_templates.get(season, [])
    if not templates:
        return "No templates for this season."
    
    template = random.choice(templates)
    return f"Haiku for {season.capitalize()}:\n" + "\n".join(template) + "\n"

if __name__ == "__main__":
    print("Seasonal Haikus (one per season):\n")
    for season in seasons:
        haiku = generate_haiku(season)
        print(haiku)
        print("-" * 20)