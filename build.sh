#!/usr/bin/env bash
# Install system-level dependencies for WeasyPrint (Pango/Cairo)
apt-get update && apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2

# Install Python dependencies
pip install -r requirements.txt
