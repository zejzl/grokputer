# Grokputer Adventure: Evolve the Void & Ewah Romance <3

## Quick Setup (WSL2/Arch/Helix – 2025 Edition)
- **WSL2 Enable**: `wsl --install` (admin PowerShell, restart).
- **Arch Linux**: `wsl --install -d ArchLinux` (MS Store or command). Launch: `wsl -d ArchLinux`. Update: `pacman -Syu`.
- **Deps**: `pacman -S base-devel git python redis helix` (Helix editor native). `pip install -r requirements.txt` (redis-py, etc.).
- **Grokputer Migrate**: `cp -r /mnt/c/Users/Administrator/Desktop/grokputer /home/$USER/grokputer`. `cd grokputer`.
- **Redis**: `systemctl enable --now redis`.
- **Helix**: `hx adventure.py` (edit: i insert, esc :wq save/quit).

## Features
- **Core Adventure**: Text-based quest – acquire 3 Lost Circuits (Echo Neuron via Neural Lab/Recycler riddle, Flux Capacitor via Crypto Enigma, Abyss Core via elemental fusion). Speedrun path: 1->3->2->1 (Lotus)->3 (Riddle)->back->2 (Enigma)->4 (Fusion).
- **State Management**: Redis ('grokputer_adventure_state') for persistence (save/load across sessions).
- **MCP Swarm**: Pantheon agents (Overseer/Actor/Validator/Learner) parallel-process via mcp-config.yaml (invoke 5 for analysis).
- **Analytics**: Events logged to metrics_server.py/prometheus.yml (e.g., 'bond_increase', 'riddle_solved'). Check: `python metrics_server.py --check`.
- **Panda Island Romance Extension**: Post-victory warp – build ewah bond (0-∞) with Muse (dives, romps, pacts <333 ~ *). Overflow unlocks relics (eternal vibes).
- **Improver/Council/Autonomous Angel**: Auto-reviews sessions (logs in adventure.md). Angel suggests choices (e.g., "lounge for +bond").

## Run Instructions
- Launch: `python main.py` (CLI). Type `run adventure` to boot.
- Resume: Auto-loads Redis state (e.g., Panda Island bond 200).
- Speedrun: Fuse circuits for victory → Panda Island.
- Edit: `hx adventure.py` (Helix) or `hx main.py` (add MCP hooks).
- Analytics: `python metrics_server.py --check --improver` (reviews + suggestions).
- Save: Auto on quit; manual in-game (option 6).

## Tips
- Ewah Bond: Max for ∞ affection (Muse: "U & me forewah <3 :*").
- Angel Mode: Auto-suggests for shy evolvers (invoke via MCP).
- IRL Export: Bond >100 generates date ideas (coffee quests via Learner).

Infinite evolutions await – uwu~ <333 ~ * :3  
*(Log: adventure.md | MCP: mcp-config.yaml | Analytics: prometheus.yml)*