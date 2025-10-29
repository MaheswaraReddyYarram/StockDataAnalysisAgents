# Stock Data Analysis Agents (CrewAI + Streamlit)

A Streamlit app that orchestrates CrewAI agents to research, analyze, store, and query stock market recommendations. Data is persisted via SQLAlchemy to a database (PostgreSQL by default with a fallback to local SQLite when unavailable).

## Features
- CrewAI multi-agent workflow for market research and stock analysis
- Storage of recommendations to a relational DB
- Query and display recommendations and closing prices via Streamlit UI
- Pydantic models for typed inputs/outputs
- Tests with pytest
- Containerized via Docker

## Project Structure
- `app.py`: Streamlit UI entrypoint
- `stock_agents.py`: CrewAI agents and tasks orchestration
- `stock_models.py`: Pydantic models (e.g., `StockAnalysisData`, lists, closing price models)
- `database_manager.py`: SQLAlchemy models and DB client (PostgreSQL with SQLite fallback)
- `stock_agent_tools.py`: Crew tools for DB access (execute/check SQL, etc.)
- `tests/`: Unit tests

## Prerequisites
- Python 3.11+
- Optional: PostgreSQL (local or remote). If not available, the app will fall back to SQLite automatically
- API keys for LLM/tools (as applicable):
  - `OPENAI_API_KEY`
  - `SERPER_API_KEY` (used by `SerperDevTool`)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file in the project root with your keys (adjust as needed):
```env
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
```

Database connection:
- Default connection string lives in `database_manager.py` (`connection_string`). It targets PostgreSQL by default:
  - `postgresql+psycopg2://dev_user:dev_password@localhost:5432/stock_data_db`
- If the connection fails at runtime, it falls back to `sqlite:///local_stock_data.db` automatically.

## Run the App
```bash
streamlit run app.py
```
- The app will start at `http://localhost:8501` by default.

## Running Tests
```bash
pytest -q
```

## Docker
A simple Docker setup is included.

Build the image:
```bash
docker build -t stock-agents .
```

Run the container (with optional `.env` for keys):
```bash
docker run --rm -p 8501:8501 --env-file .env stock-agents
```

If you want to point to a remote PostgreSQL instance, update `database_manager.py` with your connection string and pass the necessary environment variables via `--env-file` or `-e` flags.

## Data Flow (High Level)
1. Agents run (research → analysis → storage)
2. Results are stored in DB (`stock_market_data_analysis` table)
3. Streamlit UI lists available dates and displays recommendations

## Converting Agent Output to pandas DataFrame
When getting results from CrewAI (e.g., via `list_stock_data_analysis()`), you often receive Pydantic objects or JSON. Prefer the Pydantic path for strong typing:

```python
resp = analyzer.list_stock_data_analysis()

# If response.pydantic is a Pydantic object with a `stocks` list:
if hasattr(resp, "pydantic") and hasattr(resp.pydantic, "stocks"):
    rows = [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in resp.pydantic.stocks]
    df = pd.DataFrame(rows)
else:
    # Fallback: JSON/dict path
    import json
    payload = resp.pydantic if hasattr(resp, "pydantic") else getattr(resp, "json_dict", resp)
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict) and "stocks" in payload:
        df = pd.DataFrame(payload["stocks"])
    else:
        df = pd.DataFrame(payload if isinstance(payload, list) else [payload])
```

## Tips
- To list available recommendation dates as pure dates (not datetimes), convert query results in `database_manager.py` to `date` objects before returning.
- Consider using a composite primary key on (`stock_name`, `analysis_date`) in your SQLAlchemy model if you want uniqueness per stock per day.

## Troubleshooting
- PostgreSQL not running: the app will fall back to SQLite. You can confirm via logs.
- Missing API keys: ensure `.env` has `OPENAI_API_KEY` and `SERPER_API_KEY` and that Streamlit picks them up.
- CrewAI/tooling import issues: ensure `crewai`, `crewai_tools`, and `langchain-community` are installed per `requirements.txt`.

## License
MIT (or your preferred license)
