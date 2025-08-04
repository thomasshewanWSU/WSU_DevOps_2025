import urllib.request
import urllib.error
import time
import json

def lambda_handler(event, context):
    # Web resource to monitor
    target_url = "https://b2c-application-web.vercel.app/"
    
    try:
        # Measure latency
        start_time = time.time()
        
        # Make HTTP request using urllib (built-in to Python)
        req = urllib.request.Request(target_url)
        req.add_header('User-Agent', 'AWS-Lambda-Canary/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            end_time = time.time()
            response_data = response.read()
            status_code = response.getcode()
        
        # Metric 1: Availability (is the site up?)
        is_available = status_code == 200
        
        # Metric 2: Latency (response time in ms)
        latency_ms = round((end_time - start_time) * 1000, 2)
        
        # Metric 3: Error rate (HTTP errors vs success)
        is_error = status_code >= 400  
        error_rate = 1 if is_error else 0  
        
        # Return metrics
        metrics = {
            "url": target_url,
            "availability": is_available,
            "latency_ms": latency_ms,
            "error_rate": error_rate,
            "status_code": status_code,
            "timestamp": time.time()
        }
        
        print(f"Canary metrics: {json.dumps(metrics)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(metrics)
        }
        
    except urllib.error.HTTPError as e:
        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)
        
        error_result = {
            "url": target_url,
            "availability": False,
            "latency_ms": latency_ms,
            "error_rate": 1,
            "status_code": e.code,
            "error": f"HTTP {e.code}: {e.reason}",
            "timestamp": time.time()
        }
        
        print(f"Canary HTTP error: {json.dumps(error_result)}")
        
        return {
            'statusCode': 200,  # Lambda succeeded, but target failed
            'body': json.dumps(error_result)
        }
        
    except Exception as e:
        # Network error or other issues
        error_result = {
            "url": target_url,
            "availability": False,
            "latency_ms": None,
            "error_rate": 1,
            "error": str(e),
            "timestamp": time.time()
        }
        
        print(f"Canary error: {json.dumps(error_result)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps(error_result)
        }