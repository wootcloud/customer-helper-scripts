This script parses Puppet data json file and pushes assets to WootCloud using custom device context API.

# Pre-requisites:
- Python 3.7 or higher
- pip 20.1.1 or higher

## Steps to run script:
- Create a python3.7 virtual environment `python3.7 -m venv /path/to/new/virtual/environment`
- Activate environment with `source path/to/environment/bin/activate`
- In puppet directory with virtual environment activated, install requirements `pip install -r requirements.txt`
- Run script `python custom_device_context.py
  --client_id <WootCloud API client id> 
  --secret_key <WootCloud API secret key> 
  --file <Puppet data json file>`
