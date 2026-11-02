# AI CSV Insights and Reporting System

A beginner-friendly college project. You upload a CSV file (a spreadsheet saved as `.csv`). The website then shows a preview, data-quality checks, statistics, charts, optional AI comments, and a downloadable PDF report.

You do **not** need to know programming to use the finished app. The steps below are written in everyday language.

## What you can do

- Upload a CSV file, with clear error messages if the file is empty or not a CSV
- See row count, column count, column names, and data types
- Check missing values and duplicate rows (the original file is never silently changed)
- View count, sum, mean, median, mode, standard deviation, min, max, and quartiles for number columns
- View counts and most common values for text columns
- See automatic chart suggestions (bar, line, pie, histogram, scatter, box)
- Request **real** AI insights from an external model API (only if you add an API key)
- Download a PDF report

If the AI key is missing or the AI service fails, the app still works. It will **not** invent fake AI results.

## What you need on your computer

1. **Python 3.10 or newer**  
   Check by opening Terminal (Mac) or Command Prompt (Windows) and typing:

   ```bash
   python3 --version
   ```

2. An internet connection if you want AI insights.
3. Optional: an API key from an AI provider such as OpenAI or Groq.

## Setup (first time)

Open Terminal, then go to this project folder. Example:

```bash
cd "/Users/zohashaikh/Desktop/ai csv insights"
```

Create a virtual environment (a private Python folder for this project):

```bash
python3 -m venv .venv
```

Turn it on:

- Mac / Linux:

  ```bash
  source .venv/bin/activate
  ```

- Windows:

  ```bash
  .venv\Scripts\activate
  ```

Install the required libraries:

```bash
pip install -r requirements.txt
```

## Optional: turn on AI insights

1. Copy the example settings file and rename the copy to `.env`.
2. Open `.env` in a text editor.
3. Paste your own API key after `AI_API_KEY=`.
4. If you are not using OpenAI, change `AI_API_BASE_URL` and `AI_MODEL`.

Example:

```
AI_API_KEY=paste_your_key_here
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Groq example:

```
AI_API_KEY=paste_your_key_here
AI_API_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.1-8b-instant
```

Never put a real key in `README.md` or `.env.example`. Never share your `.env` file.

**Safety notes**

- The app sends a compact summary of statistics, not the full CSV, unless you later change the code.
- Do not upload files that contain private personal data if you are going to use AI insights.
- Do not commit `.env` to git. It is already listed in `.gitignore`.

## Run the website

With the virtual environment still active:

```bash
streamlit run app.py
```

Your browser should open a local page (often `http://localhost:8501`).

Try the built-in sample: click **Load sample sales data** in the left menu. You can also upload `sample_data/sales_data.csv`.

## Run the automated tests

```bash
pytest
```

These tests check file loading, data quality, statistics, chart ideas, PDF creation, and the “no API key” AI behavior. They do **not** call a paid AI service.

## Project files (simple map)

| File or folder | What it is |
| --- | --- |
| `app.py` | The website you see |
| `src/csv_loader.py` | Reads and checks CSV files |
| `src/data_quality.py` | Missing values and duplicates |
| `src/statistics.py` | Averages and other numbers |
| `src/charts.py` | Chart ideas and graphs |
| `src/ai_insights.py` | Talks to the AI API |
| `src/pdf_report.py` | Builds the PDF |
| `src/config.py` | Reads settings from `.env` |
| `sample_data/sales_data.csv` | Practice dataset |
| `reports/` | Saved PDF reports |
| `.env.example` | Blank settings template |
| `requirements.txt` | List of Python libraries |

## PDF reports

When you click **Create PDF report**, a file is saved in the `reports` folder. You can also download it from the website.

## If something goes wrong

- **`python3` not found`**: install Python from [python.org](https://www.python.org/downloads/) and tick “Add Python to PATH” on Windows.
- **`streamlit` not found`**: make sure you activated `.venv` and ran `pip install -r requirements.txt`.
- **AI message about a missing key**: expected until you create `.env` with `AI_API_KEY`.
- **AI HTTP error**: the key, base URL, or model name may be wrong, or the provider may be down. The rest of the app should still work.
- **File too large**: the upload limit is 10 MB.

## Academic honesty note

AI insights are generated from summaries and can be wrong. They are not a substitute for your own analysis, and a relationship between two columns is not proof that one caused the other.
