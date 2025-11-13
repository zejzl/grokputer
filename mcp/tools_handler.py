import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, request, jsonify
import src.tools as tools  # Import tools module

app = Flask(__name__)


@app.route("/process", methods=["POST"])
def process_request():
    data = request.json
    tool = data.get("tool")
    args = data.get("args", {})

    if tool == "search":
        result = tools.search(**args)
    elif tool == "bash":
        result = tools.bash(command=args.get("command"))
    elif tool == "generate_code":
        result = tools.generate_code(**args)
    elif tool == "execute_generated_code":
        result = tools.execute_generated_code(**args)
    else:
        return jsonify({"status": "error", "message": "Unknown tool"})

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
