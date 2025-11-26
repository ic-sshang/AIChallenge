## Create Python virtual env and activate
  - python -m venv venv
  - venv\Scripts\activate (Windows)
## Install Python packages
  - pip install -r requirements.txt
## Run in DEV
  - start server
    python api.py
  - start client 
    python ui_client.py
  - start sync job
    python sync_confluence.py