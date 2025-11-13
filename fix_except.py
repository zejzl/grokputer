with open("autonomous.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    if "except KeyboardInterrupt:" in lines[i]:
        new_lines.append("except KeyboardInterrupt:\n")
        i += 1
        if i < len(lines) and 'console.print("' in lines[i]:
            new_lines.append('    console.print("\\n[green]Daemon stopped by user.[/green]")\n')
            i += 1
        if i < len(lines) and "if r:" in lines[i]:
            new_lines.append("    if r:\n")
            i += 1
        if i < len(lines) and 'r.set("daemon_stopped", "true")' in lines[i]:
            new_lines.append('        r.set("daemon_stopped", "true")\n')
            i += 1
        new_lines.append("\n")
    else:
        new_lines.append(lines[i])
        i += 1

with open("autonomous.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Fixed except block.")
