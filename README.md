# 🔍 Log Analysis Dashboard

An interactive web dashboard built with **Python + Streamlit** that parses system log files and helps detect errors, patterns and anomalies in real time.

---

##  Features

| Feature | Details |
|---|---|
| **Upload & Parse** | Drag-and-drop any `.txt` log file |
| **KPI Cards** | Total entries, ERROR / WARNING / INFO counts at a glance |
| **Bar Chart** | Log level distribution (horizontal, color-coded) |
| **Pie Chart** | Proportional level share as a donut chart |
| **Top Errors Table** | Most repeated error messages ranked by frequency |
| **Error Timeline** | Line chart of error volume over time (when timestamps detected) |
| **Raw Log Preview** | Scrollable parsed table of first 200 entries |

##  Key Highlights

- Built an interactive data dashboard using Streamlit
- Implemented log parsing using regular expressions
- Applied data aggregation using Python collections
- Visualized log patterns using charts for quick insights

---

##  Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-username/log-analysis-dashboard.git
cd log-analysis-dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Then open **http://localhost:8501** and upload `sample_logs.txt` to see it in action.

---

##  Project Structure

```
log-analysis-dashboard/
├── app.py            # Main Streamlit application
├── sample_logs.txt   # Example log file for testing
├── requirements.txt  # Python dependencies
```

---

##  Tech Stack

- **Python 3.10+**
- **Streamlit** — UI & reactive layout
- **Pandas** — data manipulation
- **Matplotlib** — charting
- **re / collections** — regex parsing & frequency counting

---

##  Supported Log Format

Any plain-text log file containing lines with standard log levels:

```
2024-03-01 08:01:20 [ERROR] Connection refused: db.internal:5432
2024-03-01 08:02:10 [WARNING] Slow query detected (892ms)
2024-03-01 08:02:15 [INFO] GET /api/products 200 OK
```

Timestamps are optional — the parser handles both formats gracefully.

---

