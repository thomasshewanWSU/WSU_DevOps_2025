# AWS Lambda Canary Monitor

Student: Thomas Shewan (22080488)  
Course: WSU DevOps 2025

## Overview

This project implements a web health monitoring canary using AWS Lambda and CDK. The system monitors web resources and collects key performance metrics: availability, response latency, and data throughput.

## Architecture

The solution uses AWS Lambda to perform HTTP health checks against target websites, with metrics sent to Amazon CloudWatch. The infrastructure is defined using AWS CDK, which provisions:

- **CloudWatchStack**: Deploys the Lambda function, schedules it to run every 5 minutes, and creates a CloudWatch dashboard with widgets for Availability, Latency, Throughput, and Content Length for each monitored website.
- **Lambda Functions**:
  - `MonitoringLambda.py`: Monitors a single web resource, measuring availability, latency, throughput, and response size.
  - `cloudWatchLambda.py`: Monitors multiple websites (from `websites.json`), collects metrics, and pushes them to CloudWatch for dashboard visualization.

The Lambda functions are triggered automatically via an EventBridge schedule (every 5 minutes), and metrics are visualized in a CloudWatch dashboard.

## Metrics Collected

1. **Availability**: HTTP 200 response indicates service availability
2. **Latency**: Response time measured in milliseconds
3. **Throughput**: Data delivery rate in bytes per second (Traffic Golden Signal)
4. **Response Size**: Content size for performance analysis

## Technical Implementation

- **Runtime**: Python 3.11
- **HTTP Library**: urllib (built-in, no external dependencies)
- **Infrastructure**: AWS CDK
- **Deployment**: CloudFormation via CDK
- **Monitoring**: Implements 3 of 4 Google SRE Golden Signals

## Project Structure

```
ThomasShewan_22080488/
├── app.py                          # CDK application entry point
├── cdk.json                        # CDK configuration
├── requirements.txt                # Dependencies
├── modules/
│   ├── MonitoringLambda.py         # Lambda: single website health check
│   ├── cloudWatchLambda.py         # Lambda: multi-site health check, CloudWatch metrics
│   └── websites.json               # List of websites to monitor
├── thomas_shewan_22080488/
│   ├── thomas_shewan_22080488_stack.py  # CDK stack definition
│   └── cloudWatchStack.py               # CDK stack for Lambda + CloudWatch dashboard
└── tests/
    └── unit/
        └── test_thomas_shewan_22080488_stack.py
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- AWS CLI configured with appropriate permissions
- Node.js and npm
- AWS CDK CLI: `npm install -g aws-cdk`

### Installation

1. Create and activate virtual environment:

```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Bootstrap CDK (first time only):

```bash
cdk bootstrap
```

4. Deploy infrastructure:

```bash
cdk synth
cdk deploy
```

## Testing

### Manual Testing

Test the deployed Lambda function through:

- AWS Console: Lambda → MonitoringLambda → Test
- AWS CLI: `aws lambda invoke --function-name MonitoringLambda output.json`

## Sample Output

Successful health check:

```json
{
  "url": "https://b2c-application-web.vercel.app/",
  "availability": true,
  "latency_ms": 245.67,
  "throughput_bps": 204081.63,
  "response_size_bytes": 50000,
  "status_code": 200,
  "timestamp": 1722654712.123
}
```

Error detection:

```json
{
  "url": "https://b2c-application-web.vercel.app/",
  "availability": false,
  "latency_ms": 1500.45,
  "throughput_bps": 0,
  "status_code": 404,
  "error": "HTTP 404: Not Found",
  "timestamp": 1722654712.123
}
```

## Configuration

### Monitoring Multiple Websites
To monitor multiple URLs, edit `modules/websites.json`:
```json
{
  "websites": [
    {"name": "Google", "url": "https://www.google.com"},
    {"name": "GitHub", "url": "https://github.com"}
  ]
}
```

For single-site monitoring, modify `target_url` in `modules/MonitoringLambda.py`:
```python
target_url = "https://your-target-website.com"
```

## Requirements Fulfilled

This project meets the assignment requirements:

- Uses AWS CDK to build a canary in Lambda function
- Operates in single AWS region
- Measures web resource metrics for monitoring
- Implements industry-standard Golden Signals monitoring
- Code managed in version control
- Documentation provided in markdown

# CloudWatchStack & Lambda Implementation

## CloudWatchStack (`cloudWatchStack.py`)

- Provisions a Lambda function with permissions to write metrics to CloudWatch.
- Schedules the Lambda to run every 5 minutes using EventBridge.
- Creates a CloudWatch dashboard with widgets for:
  - Availability
  - Latency (ms)
  - Throughput (Bytes/sec)
  - Content Length (Bytes)
- Visualizes metrics for each website listed in `websites.json`.

## Lambda Functions

### `cloudWatchLambda.py`
- Loads a list of websites from `websites.json`.
- For each site, performs an HTTP request and measures:
  - Availability (HTTP 200)
  - Latency (ms)
  - Throughput (Bytes/sec)
  - Content Length (Bytes)
- Publishes metrics to CloudWatch under the namespace `WebCrawler/Monitoring`.

### `MonitoringLambda.py`
- Monitors a single website (URL hardcoded as `target_url`).
- Measures and returns:
  - Availability
  - Latency
  - Throughput
  - Response size
- Prints metrics to logs and returns results in Lambda response.

---
For more details, see the code in `modules/cloudWatchLambda.py`, `modules/MonitoringLambda.py`, and `thomas_shewan_22080488/cloudWatchStack.py`.
