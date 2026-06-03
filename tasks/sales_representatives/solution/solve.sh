#!/bin/bash

set -euo pipefail

cat > /app/answer.json <<'EOF'
{"answer":[3,8,17,31,45,49,64,68,75,98]}
EOF
