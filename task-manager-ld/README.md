# Task Manager - LaunchDarkly Experiment Demo

A Flask-based task manager demonstrating LaunchDarkly feature flags and A/B experiments.

## Experiment

Hypothesis: Users who see progress metrics will complete more tasks.

Treatment: Progress metrics chart (enabled/disabled via progress-metrics flag)

Metrics:
- task-completed - Primary conversion metric
- progress-chart-viewed - Feature exposure
- task-created - User engagement

## Quick Start

Run locally:
    python run.py

Run with ngrok tunnel:
    python run.py --ngrok

## Demo Users

| Username | Password | Plan    |
|----------|----------|---------|
| alice    | demo     | premium |
| bob      | demo     | free    |
| carol    | demo     | free    |
| david    | demo     | premium |
| eve      | demo     | free    |

## Feature Flags

Create these flags in LaunchDarkly:

| Flag Key         | Type    | Description    |
|------------------|---------|----------------|
| dark-mode        | Boolean | Dark theme     |
| task-stats       | Boolean | Stats bar      |
| task-search      | Boolean | Search feature |
| task-categories  | Boolean | Categories     |
| task-priority    | Boolean | Priority       |
| task-due-dates   | Boolean | Due dates      |
| progress-metrics | Boolean | EXPERIMENT     |

## API Endpoints

- GET /api/flags - Current flag states
- GET /api/progress - User progress data

##After Installation, Follow these Steps
# Navigate to project
cd task-manager-ld

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Mac/Linux

# Now install packages
pip install -r requirements.txt

# Run the app
python run.py
