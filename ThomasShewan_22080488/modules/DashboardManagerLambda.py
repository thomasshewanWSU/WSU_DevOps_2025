"""
Dashboard and Alarm Manager Lambda
Triggered by DynamoDB streams when targets are added/removed/modified
Manages CloudWatch dashboards and alarms dynamically
"""
import json
import boto3
import os
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    """
    Triggered by DynamoDB streams when targets change
    Updates dashboard and alarms to match current targets
    """
    print(f"Received DynamoDB stream event: {json.dumps(event)}")
    
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        # Check if any records indicate target changes
        has_changes = False
        for record in event['Records']:
            event_name = record['eventName']
            if event_name in ['INSERT', 'REMOVE', 'MODIFY']:
                has_changes = True
                break
        
        if not has_changes:
            print("No relevant changes detected")
            return {'statusCode': 200, 'body': 'No changes to process'}
        
        print("Target changes detected - updating dashboard and alarms")
        
        # Get current state of all targets
        targets = get_all_current_targets()
        print(f"Found {len(targets)} enabled targets")
        
        # Update dashboard and alarms
        update_dashboard_with_targets(cloudwatch, targets)
        sync_alarms_with_targets(cloudwatch, targets)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully updated dashboard and alarms for {len(targets)} targets'
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_all_current_targets():
    """Get all enabled targets from DynamoDB"""
    try:
        table_name = os.environ.get('TARGETS_TABLE_NAME')
        if not table_name:
            print("TARGETS_TABLE_NAME not set")
            return []
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        response = table.scan(
            FilterExpression=Attr('enabled').eq(True)
        )
        
        items = response.get('Items', [])
        
        targets = [
            {
                'name': item['name'],
                'url': item['url']
            }
            for item in items
        ]
        
        return targets
        
    except Exception as e:
        print(f"Error reading targets from DynamoDB: {str(e)}")
        return []

def update_dashboard_with_targets(cloudwatch, targets):
    """Update CloudWatch dashboard with current targets"""
    try:
        dashboard_name = os.environ.get('DASHBOARD_NAME', 'WebMonitoringDashboard')
        
        if not targets:
            print("No targets - creating empty dashboard")
            dashboard_body = {"widgets": []}
        else:
            dashboard_body = generate_dashboard_body(targets)
        
        cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )
        
        print(f"Updated dashboard '{dashboard_name}' with {len(targets)} targets")
        
    except Exception as e:
        print(f"Error updating dashboard: {str(e)}")
        raise

def generate_dashboard_body(targets):
    """Generate CloudWatch dashboard JSON with widgets for all targets"""
    widgets = []
    
    # Overview widget - all websites availability
    widgets.append({
        "type": "metric",
        "x": 0, "y": 0, "width": 24, "height": 6,
        "properties": {
            "metrics": [
                ["WebMonitoring/Health", "Availability", "Website", target['name']]
                for target in targets
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": "ap-southeast-2",
            "title": "Website Availability Overview",
            "period": 300,
            "yAxis": {
                "left": {"min": 0, "max": 1}
            }
        }
    })
    
    # Individual widgets for each website (3 columns)
    y_position = 6
    for i, target in enumerate(targets):
        x_position = (i % 3) * 8
        if i % 3 == 0 and i > 0:
            y_position += 6
            
        website_name = target['name']
        
        # Availability + Latency widget
        widgets.append({
            "type": "metric",
            "x": x_position, "y": y_position, "width": 8, "height": 6,
            "properties": {
                "metrics": [
                    ["WebMonitoring/Health", "Availability", "Website", website_name, {"yAxis": "left"}],
                    [".", "Latency", ".", ".", {"yAxis": "right"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "ap-southeast-2",
                "title": f"{website_name} - Health",
                "period": 300,
                "yAxis": {
                    "left": {"min": 0, "max": 1},
                    "right": {"min": 0}
                }
            }
        })
    
    # Throughput comparison (if we have targets)
    if targets:
        y_position += 6
        widgets.append({
            "type": "metric",
            "x": 0, "y": y_position, "width": 24, "height": 6,
            "properties": {
                "metrics": [
                    ["WebMonitoring/Health", "Throughput", "Website", target['name']]
                    for target in targets
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "ap-southeast-2",
                "title": "Throughput Comparison",
                "period": 300
            }
        })
    
    return {"widgets": widgets}

def sync_alarms_with_targets(cloudwatch, targets):
    """Sync alarms with current targets"""
    try:
        # Get current target names
        target_names = {target['name'] for target in targets}
        
        # Get existing alarms
        existing_alarms = get_existing_website_alarms(cloudwatch)
        existing_websites = {extract_website_from_alarm_name(alarm) for alarm in existing_alarms}
        
        # Create alarms for new websites
        for target_name in target_names - existing_websites:
            create_alarms_for_website(cloudwatch, target_name)
            print(f"Created alarms for: {target_name}")
        
        # Delete alarms for removed websites
        for website in existing_websites - target_names:
            delete_alarms_for_website(cloudwatch, website)
            print(f"Deleted alarms for: {website}")
            
        print(f"Alarm sync completed - {len(target_names)} active targets")
        
    except Exception as e:
        print(f"Error syncing alarms: {str(e)}")
        raise

def get_existing_website_alarms(cloudwatch):
    """Get all existing website monitoring alarms"""
    try:
        response = cloudwatch.describe_alarms()
        
        website_alarms = [
            alarm['AlarmName'] for alarm in response['MetricAlarms']
            if any(suffix in alarm['AlarmName'] for suffix in ['-Availability-Alarm', '-Latency-Alarm', '-Throughput-Alarm'])
        ]
        
        return website_alarms
        
    except Exception as e:
        print(f"Error getting existing alarms: {str(e)}")
        return []

def extract_website_from_alarm_name(alarm_name):
    """Extract website name from alarm name"""
    return alarm_name.replace('-Availability-Alarm', '').replace('-Latency-Alarm', '').replace('-Throughput-Alarm', '')

def create_alarms_for_website(cloudwatch, website_name):
    """Create availability, latency, and throughput alarms for a website matching CDK configuration"""
    try:
        alarm_topic_arn = os.environ.get('ALARM_TOPIC_ARN')
        if not alarm_topic_arn:
            print(f"ALARM_TOPIC_ARN not set - skipping alarm creation for {website_name}")
            return
        
        # 1. Availability Alarm (simple threshold - matches CDK)
        cloudwatch.put_metric_alarm(
            AlarmName=f"{website_name}-Availability-Alarm",
            ComparisonOperator='LessThanThreshold',
            EvaluationPeriods=2,
            MetricName='Availability',
            Namespace='WebMonitoring/Health',
            Period=300,
            Statistic='Average',
            Threshold=1.0,
            ActionsEnabled=True,
            AlarmActions=[alarm_topic_arn],
            AlarmDescription=f'Alert when {website_name} is unavailable',
            Dimensions=[{'Name': 'Website', 'Value': website_name}],
            DatapointsToAlarm=2,
            TreatMissingData='breaching'
        )
        
        # 2. Latency Anomaly Detection Alarm (matches CDK exactly)
        create_anomaly_detection_alarm(
            cloudwatch=cloudwatch,
            website_name=website_name,
            metric_name='Latency',
            alarm_suffix='Latency-Alarm',
            description=f'Alert when {website_name} latency is anomalous (outside 2 standard deviations)',
            alarm_topic_arn=alarm_topic_arn,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            std_devs=2
        )
        
        # 3. Throughput Anomaly Detection Alarm (matches CDK exactly)
        create_anomaly_detection_alarm(
            cloudwatch=cloudwatch,
            website_name=website_name,
            metric_name='Throughput',
            alarm_suffix='Throughput-Alarm',
            description=f'Alert when {website_name} throughput is anomalous (outside 2 standard deviations)',
            alarm_topic_arn=alarm_topic_arn,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            std_devs=2
        )
        
        print(f"Successfully created all alarms for {website_name}")
        
    except Exception as e:
        print(f"Error creating alarms for {website_name}: {str(e)}")
        raise

def delete_alarms_for_website(cloudwatch, website_name):
    """Delete all alarms and anomaly detectors for a website"""
    # Delete alarms
    alarm_names = [
        f"{website_name}-Availability-Alarm",
        f"{website_name}-Latency-Alarm",
        f"{website_name}-Throughput-Alarm"
    ]
    
    for alarm_name in alarm_names:
        try:
            cloudwatch.delete_alarms(AlarmNames=[alarm_name])
            print(f"Deleted alarm: {alarm_name}")
        except cloudwatch.exceptions.ResourceNotFound:
            print(f"Alarm not found (already deleted): {alarm_name}")
        except Exception as e:
            print(f"Error deleting alarm {alarm_name}: {str(e)}")
    
    # Delete anomaly detectors
    for metric_name in ['Latency', 'Throughput']:
        try:
            cloudwatch.delete_anomaly_detector(
                Namespace='WebMonitoring/Health',
                MetricName=metric_name,
                Dimensions=[{'Name': 'Website', 'Value': website_name}],
                Stat='Average'
            )
            print(f"Deleted anomaly detector for {website_name} {metric_name}")
        except cloudwatch.exceptions.ResourceNotFoundException:
            print(f"Anomaly detector not found for {website_name} {metric_name}")
        except Exception as e:
            print(f"Error deleting anomaly detector for {website_name} {metric_name}: {str(e)}")

def create_anomaly_detection_alarm(cloudwatch, website_name, metric_name, alarm_suffix, 
                                 description, alarm_topic_arn, evaluation_periods=3, 
                                 datapoints_to_alarm=2, std_devs=2):
    """
    Create an anomaly detection alarm that matches CDK's AnomalyDetectionAlarm
    This replicates the exact behavior of your CDK cloudwatch.AnomalyDetectionAlarm
    """
    
    # Step 1: Create the anomaly detector (if it doesn't exist)
    try:
        cloudwatch.put_anomaly_detector(
            Namespace='WebMonitoring/Health',
            MetricName=metric_name,
            Dimensions=[{'Name': 'Website', 'Value': website_name}],
            Stat='Average'
        )
        print(f"Created anomaly detector for {website_name} {metric_name}")
    except cloudwatch.exceptions.ResourceConflictException:
        print(f"Anomaly detector already exists for {website_name} {metric_name}")
    
    # Step 2: Create the anomaly detection alarm
    # This matches your CDK AnomalyDetectionAlarm configuration exactly
    cloudwatch.put_metric_alarm(
        AlarmName=f"{website_name}-{alarm_suffix}",
        ComparisonOperator='LessThanLowerOrGreaterThanUpperThreshold',
        EvaluationPeriods=evaluation_periods,
        Metrics=[
            {
                'Id': 'm1',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'WebMonitoring/Health',
                        'MetricName': metric_name,
                        'Dimensions': [{'Name': 'Website', 'Value': website_name}]
                    },
                    'Period': 300,
                    'Stat': 'Average'
                }
            },
            {
                'Id': 'ad1', 
                'Expression': f'ANOMALY_DETECTION_FUNCTION(m1, {std_devs})'
            }
        ],
        ThresholdMetricId='ad1',
        ActionsEnabled=True,
        AlarmActions=[alarm_topic_arn],
        AlarmDescription=description,
        DatapointsToAlarm=datapoints_to_alarm,
        TreatMissingData='notBreaching'
    )