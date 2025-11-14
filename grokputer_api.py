from flask import Flask, request, jsonify
import subprocess
import sys
import os

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "Grokputer Python API is running", "timestamp": "2025-11-14"})

@app.route('/api/task', methods=['POST'])
def execute_task():
    data = request.get_json()
    task = data.get('task', '')

    if not task:
        return jsonify({"error": "No task provided"}), 400

    try:
        # Call main.py with the task
        result = subprocess.run([
            sys.executable, 'main.py', '--task', task
        ], capture_output=True, text=True, cwd=os.getcwd())

        return jsonify({
            "task": task,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)