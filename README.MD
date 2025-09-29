- Create Python virtual env and activate
  python -m venv venv
  venv\Scripts\activate
- Install Python packages
  pip install -r requirements.txt
- Run in DEV
  -- start in loal
  uvicorn app:app --reload --host 0.0.0.0 --port 8000
