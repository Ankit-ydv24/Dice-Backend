# Dice-Backend

A lightweight Flask backend that generates a rich, shareable EDA (Exploratory Data Analysis) HTML report from a CSV dataset. Upload a CSV file to the `/generate-report` endpoint and receive a downloadable HTML report with column stats, correlations, distributions, and relationships.

## Requirements

- Python 3.9+
- Packages listed in `requirements.txt`

## Quickstart (Local)

```powershell
# From the project folder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The server starts on http://127.0.0.1:5000.

## API

- POST `/generate-report`
  - Form-Data fields:
    - `dataset` (required): CSV file to analyze
    - `template` (optional): Custom HTML template; defaults to `report_template.html`
  - Response: `data_insight_report.html` file (Content-Type: text/html; attachment)

### Example request (PowerShell)

```powershell
$Form = @{
  dataset = Get-Item ".\sample.csv"
}
Invoke-RestMethod -Uri "http://127.0.0.1:5000/generate-report" -Method Post -Form $Form -OutFile "report.html"
# Now open report.html in your browser
```

Or with curl (if available):

```powershell
curl -X POST "http://127.0.0.1:5000/generate-report" -F "dataset=@sample.csv" -o report.html
```

## Notes

- Only CSV files are supported out of the box. To support Excel/other formats, update `pandas.read_*` usage in `app.py`.
- Large datasets are sampled in certain plots to keep rendering fast.
- Temporary files created during report generation are cleaned up automatically on process exit.

## Deploying

This service can be deployed behind a production WSGI server (e.g., gunicorn) on Linux. For Windows development, run `python app.py`.

## Project Layout

- `app.py` – Flask app with `/generate-report` endpoint
- `data_insight_generator.py` – Report generation logic using pandas, seaborn, matplotlib, jinja2
- `report_template.html` – HTML template used to render the EDA report
- `requirements.txt` – Python dependencies

## License

MIT (add a `LICENSE` file if you want to formalize this)
