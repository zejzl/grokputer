from flask import Flask, request, jsonify
from src.tools import search, bash, generate_code, execute_generated_code  # Import existing tools

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_request():
    data = request.json
    tool = data.get('tool')
    args = data.get('args', {})
    
    if tool == 'search':
        result = search(**args)
    elif tool == 'bash':
        result = bash(command=args.get('command'))
    elif tool == 'generate_code':
        result = generate_code(**args)
    elif tool == 'execute_generated_code':
        result = execute_generated_code(**args)
    else:
        return jsonify({'status': 'error', 'message': 'Unknown tool'})
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)