from flask import Flask


app = Flask(__name__)

@app.route('/healthz', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200