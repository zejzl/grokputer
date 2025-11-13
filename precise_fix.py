with open("autonomous.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i in range(len(lines)):
    if (
        'console.print("' in lines[i]
        and i + 1 < len(lines)
        and '[green]Daemon stopped by user.[/green"]' in lines[i + 1]
    ):
        lines[i] = '    console.print("\\n[green]Daemon stopped by user.[/green]")\n'
        del lines[i + 1]  # Remove the next line
        break

with open("autonomous.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Precise fix applied.")
