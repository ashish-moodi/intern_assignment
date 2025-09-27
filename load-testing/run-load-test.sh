#!/bin/bash

# Load testing script for Stories API
# Requires k6 to be installed: https://k6.io/docs/getting-started/installation/

set -e

BASE_URL=${1:-"http://localhost:8000"}
DURATION=${2:-"5m"}

echo "🚀 Starting load test against $BASE_URL"
echo "⏱️  Duration: $DURATION"
echo ""

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo "❌ k6 is not installed. Please install it first:"
    echo "   https://k6.io/docs/getting-started/installation/"
    exit 1
fi

# Run the load test
echo "📊 Running load test..."
k6 run \
  --env BASE_URL="$BASE_URL" \
  --duration="$DURATION" \
  k6-load-test.js

echo ""
echo "✅ Load test completed!"
echo "📈 Check the metrics above for performance insights."
