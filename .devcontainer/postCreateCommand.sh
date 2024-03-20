pip install --upgrade pip
pip install -r .devcontainer/requirements.txt
uvicorn app.main:app --reload --log-config /workspaces/biblia.filipelopes.me/log_conf.yaml