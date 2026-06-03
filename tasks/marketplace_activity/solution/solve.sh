#!/bin/bash

set -euo pipefail

cat > /app/answer.json <<'EOF'
{"Barcelona":["Art","Books","Decor"],"Bilbao":["Bags","Formalwear","Women's Shoes"],"Madrid":["Fitness","Garden","Pets"],"Sevilla":["Computers","Consoles","Video Games"],"Valencia":["Bicycles","Furniture","Tools"],"Zaragoza":["Cameras","Collectibles","Musical Instruments"]}
EOF
