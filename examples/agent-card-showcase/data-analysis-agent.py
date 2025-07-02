from phlow_auth import PhlowAuth
from flask import Flask, request, jsonify

app = Flask(__name__)

# Define your agent's capabilities with an Agent Card
phlow = PhlowAuth(
    agent_card={
        "name": "DataWizard",
        "description": "AI agent specialized in data analysis and visualization",
        "skills": ["data-analysis", "visualization", "statistical-modeling"],
        "endpoints": {
            "analyze": {"method": "POST", "path": "/analyze"},
            "visualize": {"method": "POST", "path": "/visualize"}
        }
    }
)

# Your agent's endpoints - protected automatically
@app.route('/analyze', methods=['POST'])
@phlow.authenticate()
def analyze():
    data = request.json
    dataset = data.get('dataset')
    analysis_type = data.get('analysis_type')
    # Perform analysis...
    return jsonify({
        "results": "Analysis complete",
        "requestedBy": request.agent['name']
    })

# Agent card automatically exposed
@app.route('/.well-known/agent.json')
def agent_card():
    return phlow.well_known_handler()