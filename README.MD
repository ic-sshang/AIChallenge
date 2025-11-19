## Create Python virtual env and activate
  - python -m venv venv
  - venv\Scripts\activate (Windows)
## Install Python packages
  - pip install -r requirements.txt
## Run in DEV
  - start in loal
  uvicorn app:app --reload --host 0.0.0.0 --port 8000
 - go to localhost:8000