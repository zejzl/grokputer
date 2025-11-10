import re
import random
from typing import Tuple

def parse_dice_notation(notation: str) -> Tuple[int, int, int]:
    """Parse dice notation like '2d6+3' into (num_dice, sides, modifier). Defaults: 1, sides, 0."""
    # Pattern: optional num, 'd', sides, optional +/-
    pattern = r'^(?P<num>\d+)?d(?P<sides>\d+)(?P<mod>[+-]\d+)?$'
    match = re.match(pattern, notation.lower().strip())
    if not match:
        raise ValueError(f'Invalid dice notation: {notation}')
    
    num = int(match.group('num')) if match.group('num') else 1
    sides = int(match.group('sides'))
    mod = int(match.group('mod')) if match.group('mod') else 0
    return num, sides, mod

def roll_dice(notation: str) -> str:
    """Roll dice based on notation (e.g., '2d6' -> sum of 2 d6 rolls). Returns formatted result."""
    try:
        num, sides, mod = parse_dice_notation(notation)
        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls) + mod
        return f'Rolled {notation}: {rolls} + {mod} = **{total}** (individual: {rolls})'
    except ValueError as e:
        return f'Error: {e}'

# Example usage
if __name__ == '__main__':
    print(roll_dice('2d6'))
    print(roll_dice('1d20+5'))
    print(roll_dice('d8-2'))