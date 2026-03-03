# Task Manager - LaunchDarkly Experimentation Platform

![LaunchDarkly](https://img.shields.io/badge/LaunchDarkly-Experimentation-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![Flask](https://img.shields.io/badge/Flask-3.0+-lightgrey)

---

## 🧑‍💼 Who I Am

Task Manager is a full-stack productivity application designed by myself, **Vaishnavi Panchal**, to demonstrate advanced feature management and A/B experimentation using LaunchDarkly. The project showcases how modern tech companies safely deploy features, run experiments, and make data-driven decisions.

**Contact**: vaishnavi.panchal@sjsu.edu

---

## 💡 Inspiration

The inspiration behind Task Manager came from wanting to understand how large scale companies roll out features to millions of users without breaking things. I discovered **LaunchDarkly**, a platform that enables feature flags, A/B testing, and progressive rollouts.

Many developers understand basic feature toggles, but I wanted to go deeper. I asked myself: *"How can I demonstrate the full power of feature management from experimentation to user segmentation to data-driven decisions?"* The goal was to build something that demonstrates modern software delivery practices.

---

## 📍 What It Does

Task Manager allows users to:

- **Create and manage tasks** with an easy to use interface
- **Track progress visually** with circular progress charts (for some users)
- **See personalized experiences** based on A/B test groups and user attributes

The application is designed to demonstrate:

- **A/B Experimentation**: Testing whether progress metrics increase task completion
- **User Segmentation**: Premium vs. free tier feature targeting
- **Progressive Rollouts**: 50/50 randomized feature splits
- **Event Tracking**: Custom metrics for behavioral analysis

The application utilizes these feature flags:
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

These were the metrics that were analyzed:
- task-completed: Primary conversion metric
- progress-chart-viewed: Feature exposure
- task-created: User engagement

---

## Demo Users:

These are the users registered to demonstrate TaskManager capabilities:

| Username | Password | Plan    |
|----------|----------|---------|
| alice    | demo     | premium |
| bob      | demo     | free    |
| carol    | demo     | free    |
| david    | demo     | premium |
| eve      | demo     | free    |

---

## 🛠️ How I Built It

Task Manager was built using a modern full-stack approach with LaunchDarkly integration:

### Backend
- Implemented **Flask** web framework for routing and business logic
- Designed **SQLite** database with user authentication and task management
- Integrated **LaunchDarkly Python SDK** for feature flags and experimentation
- Built context system to send user attributes (plan, name, email) to LaunchDarkly
- Created event tracking system for custom metrics (`task-completed`, `user-login`)

### Frontend
- Designed responsive UI with HTML5, CSS3, and vanilla JavaScript
- Implemented **Chart.js** for circular progress visualization
- Created an easy to update task tracking system
  
### LaunchDarkly Configuration
- Set up **4 feature flags** with different targeting strategies
- Created **custom metric** (`task-completed`) for A/B testing
- Configured **50/50 experiment** to test progress chart effectiveness
- Implemented **attribute-based targeting** for premium features

### Architecture
- Applied clean code principles with modular functions
- Implemented error handling
- Used environment variables for secure configuration
- Designed as a demo for scalability and production deployment

---

## 🧱 Challenges I Ran Into

**Challenge 1: Events Not Reaching LaunchDarkly**
- Initial event tracking wasn't working
- Discovered network connection was blocking connections to `events.launchdarkly.com`
- **Solution**: Switched networks and added explicit `flush()` calls after each event

**Challenge 2: Small Sample Size in Experiment**
- With only 5 demo users, the 50/50 split coincidentally matched premium vs. free
- Could have appeared that the experiment was biased
- **Solution**: Documented sample size limitations and explained that production needs 100+ users per variation for statistical significance

**Challenge 4: Context Attributes for Targeting**
- Understanding how to build rich context with user attributes
- **Solution**: Studied LaunchDarkly docs and implemented custom attributes for flexible targeting rules

---

## ⏭️ What's Next For Task Manager

Future improvements include:
- **Mobile application** with LaunchDarkly Mobile SDK
- **User registration system** with OAuth integration (Google, GitHub)
- **Calendar integration** and push notifications
- **Multi-language support** with feature flag-controlled translations

The goal is to continue evolving Task Manager into a production-ready SaaS application while maintaining it as a project that demonstrates advanced LaunchDarkly capabilities.

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- LaunchDarkly account ([sign up free](https://launchdarkly.com))
- Git

### Quick Start

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/launchdarkly_demo.git
cd task-manager-ld

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Edit .env and add your LaunchDarkly SDK key
nano .env

# Run application (optional to run with ngrok)
python3 run.py --ngrok


















