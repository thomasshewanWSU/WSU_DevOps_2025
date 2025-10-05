import urllib.request
import urllib.error
import time
import json
import os
import boto3
from boto3.dynamodb.conditions import Attr

from constants import (
    METRIC_NAMESPACE,
    METRIC_AVAILABILITY,
    METRIC_LATENCY,
    METRIC_THROUGHPUT,
    DIM_WEBSITE,
    DEFAULT_WEBSITES,
    ENV_WEBSITES,
    USER_AGENT,
    DEFAULT_TIMEOUT_SECONDS,
)

def lambda_handler(event, context):
    # Initialize CloudWatch client
    cloudwatch = boto3.client('cloudwatch')
    
    targets = get_targets_from_dynamodb()
    
    # Only use DynamoDB targets 
    if not targets:
        print("No targets found in DynamoDB - nothing to monitor")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'No targets configured for monitoring',
                'results': []
            })
        }
    
    print(f"Loaded {len(targets)} targets from DynamoDB")
    #     static_websites = load_websites()
    #     for website in static_websites:
    #         targets.append({
    #             'name': website['name'],
    #             'url': website['url']
    #         })
    # Monitor each website
    all_results = []

    for website in targets: 
        result = monitor_website(website["name"], website["url"])
        all_results.append(result)
        
        # Send metrics to CloudWatch
        send_metrics_to_cloudwatch(cloudwatch, result)
    
    print(f"Monitoring completed for {len(targets)} websites")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully monitored {len(targets)} websites',
            'results': all_results
        })
    }

def load_websites():
    raw = os.environ.get(ENV_WEBSITES)
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            print("Invalid WEBSITES JSON; falling back to defaults")
    return DEFAULT_WEBSITES


def monitor_website(website_name, target_url):
    """Monitor a single website and return metrics"""
    start_time = time.time()
    try:
        # Make HTTP request
        req = urllib.request.Request(target_url)
        req.add_header('User-Agent', USER_AGENT)

        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            end_time = time.time()
            response_data = response.read()
            status_code = response.getcode()

        # Calculate metrics
        is_available = status_code == 200
        latency_ms = round((end_time - start_time) * 1000, 2)
        response_size_bytes = len(response_data)
        throughput_bps = round(response_size_bytes / (latency_ms / 1000), 2) if latency_ms > 0 else 0

        result = {
            "website_name": website_name,
            "url": target_url,
            "availability": 1 if is_available else 0,
            "latency_ms": latency_ms,
            "throughput_bps": throughput_bps,
            "response_size_bytes": response_size_bytes,
            "status_code": status_code,
            "timestamp": time.time(),
            "success": True
        }

        print(f"Success - {website_name}: {json.dumps(result)}")
        return result

    except urllib.error.HTTPError as e:
        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)

        result = {
            "website_name": website_name,
            "url": target_url,
            "availability": 0,
            "latency_ms": latency_ms,
            "throughput_bps": 0,
            "status_code": e.code,
            "error": f"HTTP {e.code}: {e.reason}",
            "timestamp": time.time(),
            "success": False
        }

        print(f"HTTP Error - {website_name}: {json.dumps(result)}")
        return result

    except Exception as e:
        result = {
            "website_name": website_name,
            "url": target_url,
            "availability": 0,
            "latency_ms": None,
            "throughput_bps": 0,
            "error": str(e),
            "timestamp": time.time(),
            "success": False
        }

        print(f"General Error - {website_name}: {json.dumps(result)}")
        return result

def send_metrics_to_cloudwatch(cloudwatch, result):
    """Send metrics to CloudWatch"""
    website_name = result["website_name"]
    timestamp = result["timestamp"]
    
    try:
        # Prepare metric data
        metric_data = []
        
        # Availability metric (0 or 1)
        metric_data.append({
            'MetricName': METRIC_AVAILABILITY,
            'Dimensions': [
                {
                    'Name': DIM_WEBSITE,
                    'Value': website_name
                }
            ],
            'Value': result["availability"],
            'Unit': 'None',
            'Timestamp': timestamp
        })
        
        # Latency metric (only if we have a valid measurement)
        if result["latency_ms"] is not None:
            metric_data.append({
                'MetricName': METRIC_LATENCY,
                'Dimensions': [
                    {
                        'Name': DIM_WEBSITE,
                        'Value': website_name
                    }
                ],
                'Value': result["latency_ms"],
                'Unit': 'Milliseconds',
                'Timestamp': timestamp
            })
        
        # Throughput metric
        metric_data.append({
            'MetricName': METRIC_THROUGHPUT,
            'Dimensions': [
                {
                    'Name': DIM_WEBSITE,
                    'Value': website_name
                }
            ],
            'Value': result["throughput_bps"],
            'Unit': 'Bytes/Second',
            'Timestamp': timestamp
        })
        
        # Send metrics to CloudWatch in batches (max 20 per call)
        for i in range(0, len(metric_data), 20):
            batch = metric_data[i:i+20]
            cloudwatch.put_metric_data(
                Namespace=METRIC_NAMESPACE,
                MetricData=batch
            )
        
        print(f"Successfully sent {len(metric_data)} metrics to CloudWatch for {website_name}")
        
    except Exception as e:
        print(f"Error sending metrics to CloudWatch for {website_name}: {str(e)}")


def get_targets_from_dynamodb():
    """
    Fetch enabled monitoring targets from DynamoDB.
    Returns list of targets in format: [{'name': '...', 'url': '...'}, ...]
    """
    try:
        table_name = os.environ.get('TARGETS_TABLE_NAME')
        if not table_name:
            print("TARGETS_TABLE_NAME not set in environment")
            return []
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        # Scan for enabled targets only
        response = table.scan(
            FilterExpression=Attr('enabled').eq(True)
        )
        
        items = response.get('Items', [])
        
        # Convert DynamoDB format to expected format
        targets = [
            {
                'name': item['name'],
                'url': item['url']
            }
            for item in items
        ]
        
        return targets
        
    except Exception as e:
        print(f"Error reading from DynamoDB: {str(e)}")
        return []