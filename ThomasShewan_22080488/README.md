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


## CI/CD Pipeline
- Stack definition: [thomas_shewan_22080488/pipeline_stack.py](thomas_shewan_22080488/pipeline_stack.py), [thomas_shewan_22080488/pipeline_stage.py](thomas_shewan_22080488/pipeline_stage.py)
- Source: GitHub repository `thomasshewanWSU/WSU_DevOps_2025` (main branch)
- Authentication: AWS Secrets Manager secret `github-token` with scopes: `repo`, `admin:repo_hook`
- Build (synth) commands:
  - cd ThomasShewan_22080488
  - npm install -g aws-cdk
  - pip install aws-cdk.pipelines
  - pip install -r requirements.txt
  - cdk synth
- Tests: runs `pytest` from [tests/unit](tests/unit) (see [tests/unit/test_thomas_shewan_22080488_stack.py](tests/unit/test_thomas_shewan_22080488_stack.py))
- Stages:
  - Manual approval gate
  - Deploys alpha stage: `alpha-ThomasShewan22080488Stack` (from [thomas_shewan_22080488/thomas_shewan_22080488_stack.py](thomas_shewan_22080488/thomas_shewan_22080488_stack.py))
- Triggers:
  - Push to `main` starts the pipeline
  - Can also start from AWS CodePipeline console


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
│   ├── MonitoringLambda.py
│   ├── AlarmLambda.py
│   └── constants.py
├── thomas_shewan_22080488/
│   ├── pipeline_stack.py
│   ├── pipeline_stage.py
│   └── thomas_shewan_22080488_stack.py
├── tests/
│   └── unit/
│       └── test_thomas_shewan_22080488_stack.py
├── app.py
├── RUNBOOK.md
└── README.md
```

## Deployment

### Pipeline (recommended)
Prereqs:
- Secrets Manager: `github-token` (scopes: `repo`, `admin:repo_hook`)
- Region: `ap-southeast-2`

Commands:
```bash
# First time per account/region
cdk bootstrap

# Deploy pipeline infrastructure
npx cdk deploy WebMonitoringPipelineStack

# Push changes to trigger pipeline
git push origin main
```
Review/approve the Manual Approval step in CodePipeline.

### Manual (legacy)
```bash
pip install -r requirements.txt
cdk bootstrap
cdk diff
cdk deploy ThomasShewan22080488Stack
```

## Monitoring
- Dashboard: CloudWatch → Dashboards → `WebsiteHealthMonitoring`
- Alarms: CloudWatch → Alarms
- Logs: CloudWatch Logs → `/aws/lambda/MonitoringLambda`
- Alarm history: DynamoDB → `AlarmLogTable`

## Operational Notes
See [`RUNBOOK.md`](RUNBOOK.md) for response steps (availability, high latency, low throughput).

## CRUD API for Target Management

### Overview
RESTful API for managing web monitoring targets dynamically without redeployment.

### API Endpoint
```bash
# Get your API URL
aws cloudformation describe-stacks --stack-name prod-ThomasShewan22080488Stack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text
```

### Quick Start
```bash
# Add a new target
curl -X POST $API_URL/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "MyWebsite", "url": "https://example.com"}'

# List all targets
curl $API_URL/targets

# Update target
curl -X PUT $API_URL/targets/{id} \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Delete target
curl -X DELETE $API_URL/targets/{id}
```

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for full API reference.

### DynamoDB Schema
- **Table**: `WebMonitoringTargets`
- **Partition Key**: `TargetId` (UUID)
- **Attributes**:
  - `name`: Display name
  - `url`: Target URL
  - `enabled`: Boolean flag
  - `created_at`: ISO timestamp
  - `updated_at`: ISO timestamp