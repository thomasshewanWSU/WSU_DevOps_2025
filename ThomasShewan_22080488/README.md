# Web Health Monitoring System

## Overview
Automated web health monitoring system using AWS Lambda, CloudWatch, and EventBridge. Monitors website availability, latency, and throughput with real-time dashboards and alarms.

## Architecture
- **AWS Lambda**: Health checks every 5 minutes
- **EventBridge**: Scheduled Lambda execution
- **CloudWatch**: Metrics storage, dashboards, and alarms
- **CDK**: Infrastructure as code

## Monitored Websites
- Google (https://www.google.com)
- Amazon (https://www.amazon.com) 
- GitHub (https://www.github.com)

## Metrics
1. **Availability**: 1 = up, 0 = down
2. **Latency**: Response time in milliseconds
3. **Throughput**: Data transfer in bytes per second

## Dashboard
CloudWatch dashboard "WebsiteHealthMonitoring" with 3 widgets:
- Website Availability (all sites)
- Response Time (all sites) 
- Throughput (all sites)

## Alarms
9 total alarms (3 per website):

| Type | Threshold | Evaluation |
|------|-----------|------------|
| Availability | < 1 | 2 consecutive failures (10 min) |
| Latency | > 5000ms | 2 out of 3 datapoints (15 min) |
| Throughput | < 1000 bytes/sec | 2 out of 3 datapoints (15 min) |

## Project Structure
```
├── modules/
│   └── MonitoringLambda.py              # Lambda function
├── thomas_shewan_22080488
│   └── thomas_shewan_22080488_stack.py  # CDK infrastructure
├── app.py                               # CDK entry point
└── README.md                            # Documentation
```

## Deployment
```bash
# Install dependencies
pip install aws-cdk-lib constructs

# Bootstrap CDK (first time)
cdk bootstrap

# Deploy
cdk deploy
```

## Configuration
To add websites, modify the array in `MonitoringLambda.py`:
```python
websites = [
    {"name": "Google", "url": "https://www.google.com"},
    {"name": "NewSite", "url": "https://www.example.com"}
]
```

## Monitoring
- **Dashboard**: AWS Console → CloudWatch → Dashboards → "WebsiteHealthMonitoring"
- **Alarms**: AWS Console → CloudWatch → Alarms
- **Logs**: AWS Console → CloudWatch → Log Groups → /aws/lambda/MonitoringLambda

## Troubleshooting
- No metrics: Check Lambda execution logs
- Alarms not working: Verify thresholds and evaluation periods
- High costs: Monitor Free Tier usage limits