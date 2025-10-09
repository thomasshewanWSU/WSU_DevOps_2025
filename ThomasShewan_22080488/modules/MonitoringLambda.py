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
    USER_AGENT,
    DEFAULT_TIMEOUT_SECONDS,
)


def lambda_handler(event, context):
    """
    Main Lambda handler for website health monitoring.
    
    Triggered by EventBridge on a schedule (every 5 minutes).
    Reads monitoring targets from DynamoDB, checks each website's health,
    and publishes metrics to CloudWatch.
    """
    # Initialize CloudWatch client for publishing custom metrics
    # CloudWatch Client API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html
    cloudwatch = boto3.client('cloudwatch')
    
    # Fetch list of enabled monitoring targets from DynamoDB
    # Targets are managed via the CRUD API (see CRUDLambda.py)
    targets = get_targets_from_dynamodb()
    
    # Early return if no targets configured
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
    
    # Monitor each website and collect results
    all_results = []

    for website in targets: 
        # Perform HTTP health check for this website
        result = monitor_website(website["name"], website["url"])
        all_results.append(result)
        
        # Publish metrics to CloudWatch for alarming and dashboards
        send_metrics_to_cloudwatch(cloudwatch, result)
    
    print(f"Monitoring completed for {len(targets)} websites")
    
    # Return success response with monitoring results
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully monitored {len(targets)} websites',
            'results': all_results
        })
    }

def monitor_website(website_name, target_url):
    """
    Perform HTTP health check on a single website.
    
    Makes an HTTP GET request and measures availability, latency, and throughput.
    Handles various failure scenarios (HTTP errors, timeouts, network issues).
    
    Python urllib documentation:
    - Request: https://docs.python.org/3/library/urllib.request.html#urllib.request.Request
    - urlopen: https://docs.python.org/3/library/urllib.request.html#urllib.request.urlopen
    - HTTPError: https://docs.python.org/3/library/urllib.error.html#urllib.error.HTTPError

    """
    start_time = time.time()
    try:
        # Create HTTP GET request with custom User-Agent
        # User-Agent identifies our monitoring system in server logs
        req = urllib.request.Request(target_url)
        req.add_header('User-Agent', USER_AGENT)

        # Execute HTTP request with timeout
        # urlopen documentation: https://docs.python.org/3/library/urllib.request.html#urllib.request.urlopen
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            end_time = time.time()
            # Read full response body to measure throughput accurately
            response_data = response.read()
            status_code = response.getcode()

        # Calculate health metrics from the HTTP response
        is_available = status_code == 200  # Only 200 OK is considered fully available
        latency_ms = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds
        response_size_bytes = len(response_data)
        # Throughput = bytes per second (avoid division by zero)
        throughput_bps = round(response_size_bytes / (latency_ms / 1000), 2) if latency_ms > 0 else 0

        # Construct successful monitoring result
        result = {
            "website_name": website_name,
            "url": target_url,
            "availability": 1 if is_available else 0,  # Binary: 1 = up, 0 = down
            "latency_ms": latency_ms,
            "throughput_bps": throughput_bps,
            "response_size_bytes": response_size_bytes,
            "status_code": status_code,
            "timestamp": time.time(),  # Unix timestamp for CloudWatch
            "success": True
        }

        print(f"Success - {website_name}: {json.dumps(result)}")
        return result

    except urllib.error.HTTPError as e:
        # Handle HTTP errors (4xx, 5xx status codes)
        # HTTPError documentation: https://docs.python.org/3/library/urllib.error.html#urllib.error.HTTPError
        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)

        result = {
            "website_name": website_name,
            "url": target_url,
            "availability": 0,  # Site is down or returning error
            "latency_ms": latency_ms,  # Still measure response time
            "throughput_bps": 0,  # No successful data transfer
            "status_code": e.code,  # HTTP error code (404, 500, etc.)
            "error": f"HTTP {e.code}: {e.reason}",
            "timestamp": time.time(),
            "success": False
        }

        print(f"HTTP Error - {website_name}: {json.dumps(result)}")
        return result

    except Exception as e:
        # Handle all other errors (timeouts, DNS failures, network issues, etc.)
        # Common exceptions:
        # - URLError: Network-level failures (DNS, connection refused)
        # - timeout: Request exceeded DEFAULT_TIMEOUT_SECONDS
        result = {
            "website_name": website_name,
            "url": target_url,
            "availability": 0,  # Site is unreachable
            "latency_ms": None,  # No valid latency measurement
            "throughput_bps": 0,
            "error": str(e),
            "timestamp": time.time(),
            "success": False
        }

        print(f"General Error - {website_name}: {json.dumps(result)}")
        return result

def send_metrics_to_cloudwatch(cloudwatch, result):
    """
    Publish website health metrics to CloudWatch.
    
    Creates custom metrics that can be used for:
    - CloudWatch Alarms (alerting on availability, latency, throughput)
    - CloudWatch Dashboards (visualizing trends)
    - CloudWatch Insights (querying and analysis)
    
    CloudWatch Metrics API:
    - PutMetricData: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/put_metric_data.html
    - Custom Metrics Guide: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html
    - Metric Data Format: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDatum.html

    """
    website_name = result["website_name"]
    timestamp = result["timestamp"]
    
    try:
        # Prepare CloudWatch metric data array
        # Each metric requires: name, dimensions, value, unit, and timestamp
        metric_data = []
        
        # AVAILABILITY METRIC: Binary indicator of website status
        # Value: 1 = website is up and responding with HTTP 200
        #        0 = website is down, unreachable, or returning errors
        # Unit: 'None' for dimensionless values
        metric_data.append({
            'MetricName': METRIC_AVAILABILITY,
            'Dimensions': [
                {
                    'Name': DIM_WEBSITE,  # Dimension allows filtering by website
                    'Value': website_name
                }
            ],
            'Value': result["availability"],
            'Unit': 'None',
            'Timestamp': timestamp
        })
        
        # LATENCY METRIC: HTTP response time in milliseconds
        # Only publish if we have a valid measurement (skip on total failures)
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
                'Unit': 'Milliseconds',  # CloudWatch standard unit for time
                'Timestamp': timestamp
            })
        
        # THROUGHPUT METRIC: Data transfer rate in bytes per second
        # Calculated as: response_size_bytes / request_duration_seconds
        # Helps identify performance degradation or content size changes
        metric_data.append({
            'MetricName': METRIC_THROUGHPUT,
            'Dimensions': [
                {
                    'Name': DIM_WEBSITE,
                    'Value': website_name
                }
            ],
            'Value': result["throughput_bps"],
            'Unit': 'Bytes/Second',  # CloudWatch standard unit for rate
            'Timestamp': timestamp
        })
        
        # Publish metrics to CloudWatch in batches
        # CloudWatch PutMetricData has a limit of 20 metrics per request
        # PutMetricData limits: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_limits.html
        for i in range(0, len(metric_data), 20):
            batch = metric_data[i:i+20]
            cloudwatch.put_metric_data(
                Namespace=METRIC_NAMESPACE,  # Groups related metrics together
                MetricData=batch
            )
        
        print(f"Successfully sent {len(metric_data)} metrics to CloudWatch for {website_name}")
        
    except Exception as e:
        # Log error but don't fail the entire monitoring run
        # One website's metric failure shouldn't affect others
        print(f"Error sending metrics to CloudWatch for {website_name}: {str(e)}")


def get_targets_from_dynamodb():
    """
    Retrieve enabled monitoring targets from DynamoDB.
    
    Reads from the WebMonitoringTargets table (managed via CRUD API).
    Only returns targets where enabled=True, allowing selective monitoring.
    
    DynamoDB Operations:
    - Table.scan: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/scan.html
    - FilterExpression: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/customizations/dynamodb.html#ref-valid-dynamodb-conditions
    - Attr: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/customizations/dynamodb.html#boto3.dynamodb.conditions.Attr

    """
    try:
        # Get table name from environment variable (set by CDK)
        table_name = os.environ.get('TARGETS_TABLE_NAME')
        if not table_name:
            print("TARGETS_TABLE_NAME not set in environment")
            return []
        
        # Initialize DynamoDB resource and get table reference
        # DynamoDB Resource: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#service-resource
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        # Scan table with filter for enabled targets only
        # Note: Scan reads all items (acceptable for small tables)
        # For large tables, consider using Query with a GSI
        response = table.scan(
            FilterExpression=Attr('enabled').eq(True)
        )
        
        items = response.get('Items', [])
        
        # Transform DynamoDB items to simplified format for monitoring
        # Only extract the fields needed for health checks
        targets = [
            {
                'name': item['name'],
                'url': item['url']
            }
            for item in items
        ]
        
        return targets
        
    except Exception as e:
        # Log error and return empty list to allow Lambda to continue
        # This prevents one DynamoDB issue from breaking all monitoring
        print(f"Error reading from DynamoDB: {str(e)}")
        return []