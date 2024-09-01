#!/bin/bash

python3 -m venv venv_miner
source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)
echo "PYTHONPATH is set to $PYTHONPATH"
NETWORK_TYPE=${1:-mainnet}
cd src
python3 subnet/miner/miner.py $NETWORK_TYPE
