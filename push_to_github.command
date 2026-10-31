#!/bin/bash
cd "$(dirname "$0")"
echo "=================================================="
echo "  Pushing Annapurna Platform to GitHub"
echo "  Repo: https://github.com/akshay29062008/smart.food.ai"
echo "=================================================="
echo ""
git push origin main
echo ""
echo "Done! Press any key to close."
read -n 1
