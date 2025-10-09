# Web Health Monitoring System

## Overview
Automated web health monitoring system with dynamic target management. Monitors website availability, latency, and throughput with real-time dashboards and automated alarm creation.

## Architecture Components

### Lambda Functions (4)
1. **CRUD Lambda** (`CRUDLambda.py`)
   - Handles API Gateway requests for managing monitoring targets
   - Operations: Create, Read, Update, Delete targets
   - Stores targets in DynamoDB

2. **Monitoring Lambda** (`MonitoringLambda.py`)
   - Triggered every 5 minutes by EventBridge
   - Performs HTTP health checks on all enabled targets
   - Publishes metrics to CloudWatch (availability, latency, throughput)

3. **Infrastructure Lambda** (`InfrastructureLambda.py`)
   - Triggered by DynamoDB Streams when targets change
   - Auto-creates CloudWatch alarms for new websites
   - Auto-deletes alarms when websites removed
   - Updates dashboard widgets dynamically

4. **Alarm Logger Lambda** (`AlarmLambda.py`)
   - Subscribes to SNS alarm topic
   - Logs all alarm state changes to DynamoDB for audit trail

### AWS Services
- **API Gateway**: RESTful API for target management
- **DynamoDB**: Stores targets (WebMonitoringTargets) and alarm logs (AlarmLogTable)
- **DynamoDB Streams**: Triggers infrastructure updates on table changes
- **EventBridge**: Scheduled monitoring (every 5 minutes)
- **CloudWatch**: Metrics, alarms, and dashboard
- **SNS**: Alarm notifications (email + Lambda)
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
  - Deploys alpha stage: `alpha-ThomasShewan22080488Stack`
  - Deploys prod stage: `prod-ThomasShewan22080488Stack` - has manual approval
- Triggers:
  - Push to `main` starts the pipeline
  - Can also start from AWS CodePipeline console


## Metrics
Published to CloudWatch namespace: `WebMonitoring/Health`

1. **Availability**: 1 = up, 0 = down
2. **Latency**: Response time in milliseconds
3. **Throughput**: Bytes per second (response_size / request_duration)

Dimension: `Website` (target name)

## Alarms (Per Website)
Automatically created/deleted by Infrastructure Lambda when targets are added/removed.

**3 alarms per website:**
1. **Availability Alarm**
   - Triggers when site is down (< 1)
   - Evaluation: 2 consecutive 5-minute periods

2. **Latency Alarm**
   - Uses CloudWatch Anomaly Detection (2 standard deviations)
   - Triggers when response time is abnormal
   - Evaluation: 2 out of 3 periods

3. **Throughput Alarm**
   - Uses CloudWatch Anomaly Detection (2 standard deviations)
   - Triggers when data transfer rate is abnormal
   - Evaluation: 2 out of 3 periods

**Notification Flow:**
CloudWatch Alarm → SNS Topic → Email + Alarm Logger Lambda → DynamoDB

## Dashboard
CloudWatch dashboard: `WebsiteHealthMonitoring`

**Widgets (auto-updated):**
- Availability: All monitored websites
- Latency: Response times across all sites
- Throughput: Data transfer rates
- Lambda Operational Metrics: Duration, invocations, errors, memory

Infrastructure Lambda automatically adds/removes website metrics as targets change.

## Project Structure
```
├── modules/
│   ├── CRUDLambda.py            # API Gateway handler
│   ├── MonitoringLambda.py      # Health check executor
│   ├── InfrastructureLambda.py  # Alarm/dashboard manager
│   ├── AlarmLambda.py           # Alarm event logger
│   └── constants.py             # Shared configuration
├── thomas_shewan_22080488/
│   ├── thomas_shewan_22080488_stack.py  # Main infrastructure
│   ├── pipeline_stack.py                # CI/CD pipeline
│   └── pipeline_stage.py                # Multi-stage deployment
├── tests/
│   ├── unit/                    # Unit tests (mocked)
│   ├── functional/              # Direct Lambda tests
│   └── integration/             # End-to-end API tests
├── app.py                       # CDK app entry point
├── API_DOCUMENTATION.md
├── RUNBOOK.md
└── README.md
```

## Deployment

### Pipeline (recommended) - Just commit the repo code or...
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


## Monitoring & Logs
- **Dashboard**: CloudWatch → Dashboards → `WebsiteHealthMonitoring`
- **Alarms**: CloudWatch → Alarms (auto-created per website)
- **Lambda Logs**: CloudWatch Logs → `/aws/lambda/{function-name}`
- **Alarm History**: DynamoDB → `AlarmLogTable` (audit trail)
- **Targets**: DynamoDB → `WebMonitoringTargets`

## Operational Notes
See [`RUNBOOK.md`](RUNBOOK.md) for troubleshooting and incident response.

## CRUD API

### Quick Reference
```bash
# List targets
curl $API_URL/targets

# Add target
curl -X POST $API_URL/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "Example", "url": "https://example.com"}'

# Update target (disable monitoring)
curl -X PUT $API_URL/targets/{id} \
  -d '{"enabled": false}'

# Delete target
curl -X DELETE $API_URL/targets/{id}
```

**Full documentation**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

### What Happens When You Add a Target
1. CRUD Lambda writes to DynamoDB `WebMonitoringTargets`
2. DynamoDB Stream triggers Infrastructure Lambda
3. Infrastructure Lambda creates 3 CloudWatch alarms
4. Infrastructure Lambda adds target to dashboard widgets
5. Monitoring Lambda picks up target on next scheduled run (within 5 minutes)