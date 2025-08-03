# AWS Lambda Canary Monitor

Student: Thomas Shewan (22080488)  
Course: WSU DevOps 2025

## Overview

This project implements a web health monitoring canary using AWS Lambda and CDK. The system monitors web resources and collects three key metrics: availability, response latency, and error rates.

## Architecture

The solution uses AWS Lambda to perform HTTP health checks against target websites. The function is deployed using AWS CDK for infrastructure as code. Currently configured for manual triggering with automatic scheduling planned for future implementation.

## Metrics Collected

1. **Availability**: HTTP 200 response indicates service availability
2. **Latency**: Response time measured in milliseconds
3. **Error Rate**: Detection of HTTP 4xx/5xx status codes

## Technical Implementation

- **Runtime**: Python 3.11
- **HTTP Library**: urllib (built-in, no external dependencies)
- **Infrastructure**: AWS CDK
- **Deployment**: CloudFormation via CDK

## Project Structure

```
ThomasShewan_22080488/
├── app.py                          # CDK application entry point
├── cdk.json                        # CDK configuration
├── requirements.txt                # Dependencies
├── modules/
│   └── MonitoringLambda.py                # Lambda function implementation
├── thomas_shewan_22080488/
│   └── thomas_shewan_22080488_stack.py  # CDK stack definition
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

- AWS Console: Lambda → WHCanaryLambda → Test
- AWS CLI: `aws lambda invoke --function-name WHCanaryLambda output.json`

### Unit Tests

```bash
python -m pytest tests/ -v
```

## Sample Output

Successful health check:

```json
{
  "url": "https://b2c-application-web.vercel.app/",
  "availability": true,
  "latency_ms": 245.67,
  "error_rate": 0,
  "status_code": 200,
  "timestamp": 1722654712.123
}
```

Error detection:

```json
{
  "url": "https://b2c-application-web.vercel.app/",
  "availability": false,
  "latency_ms": null,
  "error_rate": 1,
  "error": "HTTP 404: Not Found",
  "timestamp": 1722654712.123
}
```

## Configuration

To monitor a different URL, modify `target_url` in `modules/WHLambda.py`:

```python
target_url = "https://your-target-website.com"
```

## Troubleshooting

Logs are available in CloudWatch under `/aws/lambda/WHCanaryLambda`.

To remove all resources: `cdk destroy`

## Requirements Fulfilled

This project meets the assignment requirements:

- Uses AWS CDK to build a canary in Lambda function
- Operates in single AWS region
- Measures web resource metrics for monitoring
- Code managed in version control
- Documentation provided in markdown
