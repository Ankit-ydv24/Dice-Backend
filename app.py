from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import os
from data_insight_generator import DataInsightGenerator
import tempfile
import atexit

app = Flask(__name__)
CORS(app)

tmp_report_files = []  # Track temp files for cleanup

def cleanup_tmp_files():
    for path in tmp_report_files:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
atexit.register(cleanup_tmp_files)

@app.route('/generate-report', methods=['POST'])
def generate_report():
    if 'dataset' not in request.files:
        return jsonify({'error': 'No dataset file provided'}), 400
    dataset_file = request.files['dataset']
    template_file = request.files.get('template')

    # Save uploaded files to temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_path = os.path.join(tmpdir, dataset_file.filename)
        dataset_file.save(dataset_path)
        df = pd.read_csv(dataset_path)

        # Use uploaded template or default
        if template_file:
            template_path = os.path.join(tmpdir, template_file.filename)
            template_file.save(template_path)
        else:
            template_path = 'report_template.html'

        # Generate report and save to a NamedTemporaryFile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
            generator = DataInsightGenerator(df)
            generator.generate_report(template_path=template_path)
            generator.save_report(tmpfile.name)
            tmp_report_files.append(tmpfile.name)
            response = send_file(tmpfile.name, as_attachment=True, download_name='data_insight_report.html', mimetype='text/html')
        return response

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=debug, port=port)