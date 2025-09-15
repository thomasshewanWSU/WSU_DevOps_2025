# Web Health Monitoring System

## Overview
Automated web health monitoring system using AWS Lambda, CloudWatch, and EventBridge. Monitors website availability, latency, and throughput with real-time dashboards, static SLO-style thresholds, and alarm logging.

## Architecture
- **AWS Lambda**: Health checks every 5 minutes
- **EventBridge**: Triggers monitoring Lambda
- **CloudWatch**: Custom metrics, alarms, dashboard
- **SNS**: Alarm notifications (email + Lambda subscriber)
- **DynamoDB**: Persistent alarm log
- **CDK**: Infrastructure as code

## Monitored Websites
Configured via:
- Environment variable `WEBSITES` (JSON array) OR
- Default list in [`modules/constants.py`](modules/constants.py)

Current defaults:
- Google (https://www.google.com)
- Amazon (https://www.amazon.com)
- GitHub (https://www.github.com)

## Metrics
1. **Availability** (`Availability`): 1 = up, 0 = failure
2. **Latency** (`Latency`): Milliseconds per request
3. **Throughput** (`Throughput`): Bytes per second (response_size_bytes / request_time)

Namespace: `WebMonitoring/Health`  
Dimension: `Website`

## Dashboard
CloudWatch dashboard: `WebsiteHealthMonitoring`  
Widgets:
- Availability (all sites)
- Latency (all sites)
- Throughput (all sites)

## Static Alarm Thresholds (Per Site)
Defined centrally in [`modules/constants.py`](modules/constants.py) under `THRESHOLDS`.

| Site    | Latency > (ms) | Throughput < (B/s) |
|---------|----------------|--------------------|
| Google  | 1000           | 15000              |
| Amazon  | 2000           | 90000              |
| GitHub  | 1000           | 600000             |
| Default (fallback) | 1500 | 200000 |

Evaluation (all):
- Period: 5 minutes
- Breach: 2 of 2 consecutive periods (≈10 min)  
Availability alarm: triggers when value < 1 (site down)  
Latency alarm: triggers when average latency exceeds threshold  
Throughput alarm: triggers when average throughput falls below threshold

Rationale:
Thresholds set ~50–60% below recent typical performance to detect material degradation without noise.

## Alarm Notifications (SNS)
All alarms publish to an SNS topic:
- Email subscription (confirm via email on first deploy)
- Lambda subscription: [`AlarmLambda.py`](modules/AlarmLambda.py) logs events to DynamoDB table `AlarmLogTable`

Flow: CloudWatch Alarm → SNS Topic → Lambda (logger) → DynamoDB

## Alarm Logging (DynamoDB)
Each alarm event stored with:
- AlarmName
- Timestamp (UTC ISO)
- Raw Message JSON

Use for audit & trend analysis.

## Project Structure
```
├── modules/
│   ├── MonitoringLambda.py        # Metric collection & publish
│   ├── AlarmLambda.py             # Alarm event logger
│   └── constants.py               # Shared config (metrics, sites, thresholds)
├── thomas_shewan_22080488/
│   └── thomas_shewan_22080488_stack.py  # CDK stack
├── app.py                         # CDK entry point
├── RUNBOOK.md                     # Operational procedures
└── README.md
```

## Deployment
```bash
# (Optional) create & activate venv
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

# First time
cdk bootstrap

# Synthesize & review
cdk diff

# Deploy
cdk deploy
```

## Monitoring
- Dashboard: CloudWatch → Dashboards → `WebsiteHealthMonitoring`
- Alarms: CloudWatch → Alarms
- Logs: CloudWatch Logs → `/aws/lambda/MonitoringLambda`
- Alarm history: DynamoDB → `AlarmLogTable`

## Operational Notes
See [`RUNBOOK.md`](RUNBOOK.md) for response steps (availability, high latency, low throughput).

---
Last updated: Static per-site thresholds restored (replacing prior experimental dynamic alarms).