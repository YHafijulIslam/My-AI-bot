# My-AI-Bot — MT5 readiness instructions

This branch/tooling adds helpful configuration and onboarding files so the bot can be configured to run against MetaTrader 5 (MT5).

What I added
- config_manager.py — small ConfigManager used by main_bot (load/validate/get helpers)
- exness_config.json.example — example configuration you should copy to exness_config.json and fill in secrets
- requirements.txt — pin the python dependencies used by the bot (install with pip)
- .gitignore — ignore local logs and secrets

Quick setup
1. Install Python dependencies (prefer a venv):
   python -m venv venv
   source venv/bin/activate   # or venv\Scripts\activate on Windows
   pip install -r requirements.txt

2. Install MetaTrader 5 terminal on the host machine and note the full path to terminal64.exe (or terminal.exe on some installs).

3. Copy the example config and edit it with your terminal path and trading credentials (do NOT commit secrets):
   cp exness_config.json.example exness_config.json
   # Edit exness_config.json -> set mt5.terminal_path, and optionally trading/account settings

4. Run the bot:
   python main_bot.py

Notes and troubleshooting
- The bot expects the MetaTrader5 Python package which requires the MT5 terminal (the package talks to the terminal locally). Ensure the terminal is installed and the terminal_path in the config points to the executable.
- Keep exness_config.json out of version control because it contains sensitive credentials (the .gitignore added will help).
- If MT5 cannot initialize, the VotingOrchestrator will fall back to demo mode — check logs in the `logs/` directory for details.

If you want, I can now:
- Create a pull request in this repository from branch `mt5-ready` into your default branch, or
- Make additional changes (example: add a script that runs mt5.initialize with the terminal path, or add unit tests).
