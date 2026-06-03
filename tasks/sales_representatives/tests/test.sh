#!/bin/bash

set -euo pipefail

mkdir -p /logs/verifier

printf "\nGT:\n"
cat /tests/gt.json

printf "\nAnswer:\n"
cat /app/answer.json

python3 /tests/score.py > /logs/verifier/reward.txt

printf "\nReward: "
cat /logs/verifier/reward.txt
