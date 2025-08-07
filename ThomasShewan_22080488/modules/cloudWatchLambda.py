import urllib.request
import time
import json
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    with open('websites.json') as f:
        websites = json.load(f)['websites']

    for site in websites:
        metrics = check_site(site)
        send_metrics(site['name'], site['url'], metrics)

    return {"statusCode": 200, "body": "Crawl completed"}

def check_site(site):
    start_time = time.time()
    try:
        req = urllib.request.Request(site['url'], headers={'User-Agent': 'LambdaCrawler/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            latency_ms = (time.time() - start_time) * 1000
            status_code = resp.getcode()
            availability = 1 if status_code == 200 else 0
            throughput = len(data) / (latency_ms / 1000) if latency_ms > 0 else 0
            content_length = len(data)
    except:
        latency_ms = 0
        availability = 0
        throughput = 0
        content_length = 0

    return {
        "availability": availability,
        "latency_ms": latency_ms,
        "throughput_bps": throughput,
        "content_length": content_length
    }

def send_metrics(name, url, metrics):
    dims = [{'Name': 'WebsiteName', 'Value': name}]
    timestamp = datetime.utcnow()

    metric_data = [
        {"MetricName": "Availability", "Dimensions": dims, "Value": metrics['availability'], "Unit": "Count", "Timestamp": timestamp},
        {"MetricName": "Latency", "Dimensions": dims, "Value": metrics['latency_ms'], "Unit": "Milliseconds", "Timestamp": timestamp},
        {"MetricName": "Throughput", "Dimensions": dims, "Value": metrics['throughput_bps'], "Unit": "Bytes/Second", "Timestamp": timestamp},
        {"MetricName": "ContentLength", "Dimensions": dims, "Value": metrics['content_length'], "Unit": "Bytes", "Timestamp": timestamp},
    ]

    cloudwatch.put_metric_data(
        Namespace='WebCrawler/Monitoring',
        MetricData=metric_data
    )
