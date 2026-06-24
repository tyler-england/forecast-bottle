#!/bin/bash
PROJECT=/Users/.../path/to/forecast-bottle

# Build environment and activate
"$PROJECT/build-env.sh"
source "$PROJECT/venv/bin/activate"

# Run
python "$PROJECT/forecast_bottle/email_forecast.py"