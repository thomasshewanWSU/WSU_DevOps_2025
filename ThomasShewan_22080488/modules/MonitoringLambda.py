import urllib.request
import urllib.error
import time
import json
import boto3

def lambda_handler(event, context):
    # Initialize CloudWatch client
    cloudwatch = boto3.client('cloudwatch')
    
    # Website list - you can modify this list as needed
    websites = [
        {"name": "Google", "url": "https://www.google.com"},
        {"name": "Amazon", "url": "https://www.amazon.com"},
        {"name": "GitHub", "url": "https://www.github.com"}
    ]
    
    all_results = []
    
    # Monitor each website
    for website in websites:
        result = monitor_website(website["name"], website["url"])
        all_results.append(result)
        
        # Send metrics to CloudWatch
        send_metrics_to_cloudwatch(cloudwatch, result)
    
    print(f"Monitoring completed for {len(websites)} websites")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully monitored {len(websites)} websites',
            'results': all_results
        })
    }

def monitor_website(website_name, target_url):
    """Monitor a single website and return metrics"""
    start_time = time.time()
    
    try:
        # Make HTTP request
        req = urllib.request.Request(target_url)
        req.add_header('User-Agent', 'AWS-Lambda-Canary/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
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
            'MetricName': 'Availability',
            'Dimensions': [
                {
                    'Name': 'Website',
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
                'MetricName': 'Latency',
                'Dimensions': [
                    {
                        'Name': 'Website',
                        'Value': website_name
                    }
                ],
                'Value': result["latency_ms"],
                'Unit': 'Milliseconds',
                'Timestamp': timestamp
            })
        
        # Throughput metric
        metric_data.append({
            'MetricName': 'Throughput',
            'Dimensions': [
                {
                    'Name': 'Website',
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
                Namespace='WebMonitoring/Health',
                MetricData=batch
            )
        
        print(f"Successfully sent {len(metric_data)} metrics to CloudWatch for {website_name}")
        
    except Exception as e:
        print(f"Error sending metrics to CloudWatch for {website_name}: {str(e)}")