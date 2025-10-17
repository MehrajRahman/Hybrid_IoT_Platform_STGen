#!/usr/bin/env bash
set -e

echo "=== Installing CoAP dependencies ==="
python -m pip install -r protocols/coap/requirements.txt

echo "=== CoAP ready ==="
echo "Run: python -m stgen.main configs/coap.json"