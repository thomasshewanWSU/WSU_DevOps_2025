"""
Infrastructure Lambda - Dynamically manages CloudWatch alarms and dashboards
Triggered by DynamoDB Streams when targets are added/removed/updated

This Lambda function:
- Creates CloudWatch alarms when new websites are added via the CRUD API
- Deletes CloudWatch alarms when websites are removed via the CRUD API
- Updates alarms when website names change

AWS Resources:
- CloudWatch Alarms: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html#CloudWatch.Client.put_metric_alarm
- DynamoDB Streams: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html
"""
import json
import boto3
import os
from constants import (
    METRIC_NAMESPACE,
    METRIC_AVAILABILITY,
    METRIC_LATENCY,
    METRIC_THROUGHPUT,
    DIM_WEBSITE
)

cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    """
    Process DynamoDB stream events and manage monitoring infrastructure
    
    Event structure from DynamoDB Streams:
    {
        'Records': [
            {
                'eventName': 'INSERT' | 'MODIFY' | 'REMOVE',
                'dynamodb': {
                    'NewImage': {...},  # Present for INSERT and MODIFY
                    'OldImage': {...}   # Present for MODIFY and REMOVE
                }
            }
        ]
    }
    """
    alarm_topic_arn = os.environ['ALARM_TOPIC_ARN']
    dashboard_name = os.environ['DASHBOARD_NAME']
    
    for record in event['Records']:
        event_name = record['eventName']  # INSERT, MODIFY, REMOVE
        
        try:
            if event_name == 'INSERT':
                # New website added - create alarms
                new_image = record['dynamodb']['NewImage']
                website_name = new_image['name']['S']
                print(f"Processing INSERT event for website: {website_name}")
                handle_website_added(website_name, alarm_topic_arn, dashboard_name)
                
            elif event_name == 'REMOVE':
                # Website removed - delete alarms
                old_image = record['dynamodb']['OldImage']
                website_name = old_image['name']['S']
                print(f"Processing REMOVE event for website: {website_name}")
                handle_website_removed(website_name)
                
            elif event_name == 'MODIFY':
                # Website updated - check if name changed
                old_image = record['dynamodb']['OldImage']
                new_image = record['dynamodb']['NewImage']
                old_name = old_image['name']['S']
                new_name = new_image['name']['S']
                
                if old_name != new_name:
                    # Name changed - delete old alarms, create new ones
                    print(f"Processing MODIFY event: {old_name} -> {new_name}")
                    handle_website_removed(old_name)
                    handle_website_added(new_name, alarm_topic_arn, dashboard_name)
                else:
                    print(f"Website {new_name} modified but name unchanged - no action needed")
                    
        except Exception as e:
            print(f"Error processing record: {str(e)}")
            print(f"Record: {json.dumps(record)}")
            # Continue processing other records even if one fails
            continue
    
    return {
        'statusCode': 200,
        'body': json.dumps('Infrastructure updated successfully')
    }


def handle_website_added(website_name, alarm_topic_arn, dashboard_name):
    """
    Create CloudWatch alarms for a new website
    
    Creates three alarms:
    1. Availability Alarm - alerts when site is down
    2. Latency Alarm - alerts when response time is anomalous
    3. Throughput Alarm - alerts when data transfer rate is anomalous
    
    Also updates the CloudWatch dashboard to include widgets for the new website.
    """
    print(f"Creating alarms for {website_name}")
    
    try:
        # Create Availability Alarm
        # Alerts when the website becomes unavailable (availability < 1)
        cloudwatch.put_metric_alarm(
            AlarmName=f"{website_name}-Availability-Alarm",
            AlarmDescription=f"Alert when {website_name} is unavailable",
            MetricName=METRIC_AVAILABILITY,
            Namespace=METRIC_NAMESPACE,
            Statistic='Average',
            Dimensions=[{'Name': DIM_WEBSITE, 'Value': website_name}],
            Period=300,  # 5 minutes
            EvaluationPeriods=2,  # Check over 2 periods (10 minutes)
            DatapointsToAlarm=2,  # Must breach threshold for both periods
            Threshold=1.0,  # Alert when < 1 (site is down)
            ComparisonOperator='LessThanThreshold',
            TreatMissingData='breaching',  # Missing data = alarm
            AlarmActions=[alarm_topic_arn]
        )
        print(f"  ✓ Created Availability alarm for {website_name}")
        
        # Create Latency Alarm (with anomaly detection)
        # Alerts when response time deviates from normal patterns
        cloudwatch.put_metric_alarm(
            AlarmName=f"{website_name}-Latency-Alarm",
            AlarmDescription=f"Alert when {website_name} latency is anomalous (outside 2 standard deviations)",
            Metrics=[
                {
                    'Id': 'm1',
                    'ReturnData': True,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': METRIC_NAMESPACE,
                            'MetricName': METRIC_LATENCY,
                            'Dimensions': [{'Name': DIM_WEBSITE, 'Value': website_name}]
                        },
                        'Period': 300,  # 5 minutes
                        'Stat': 'Average'
                    }
                },
                {
                    'Id': 'ad1',
                    'Expression': 'ANOMALY_DETECTION_BAND(m1, 2)',  # 2 std deviations
                    'Label': 'Latency (expected)'
                }
            ],
            EvaluationPeriods=3,  # Check over 3 periods (15 minutes)
            DatapointsToAlarm=2,  # Must breach for 2 out of 3 periods
            ComparisonOperator='LessThanLowerOrGreaterThanUpperThreshold',
            ThresholdMetricId='ad1',  # Compare against anomaly detection band
            TreatMissingData='notBreaching',  # Missing data = don't alarm
            AlarmActions=[alarm_topic_arn]
        )
        print(f"  ✓ Created Latency alarm for {website_name}")
        
        # Create Throughput Alarm (with anomaly detection)
        # Alerts when data transfer rate deviates from normal patterns
        cloudwatch.put_metric_alarm(
            AlarmName=f"{website_name}-Throughput-Alarm",
            AlarmDescription=f"Alert when {website_name} throughput is anomalous (outside 2 standard deviations)",
            Metrics=[
                {
                    'Id': 'm1',
                    'ReturnData': True,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': METRIC_NAMESPACE,
                            'MetricName': METRIC_THROUGHPUT,
                            'Dimensions': [{'Name': DIM_WEBSITE, 'Value': website_name}]
                        },
                        'Period': 300,  # 5 minutes
                        'Stat': 'Average'
                    }
                },
                {
                    'Id': 'ad1',
                    'Expression': 'ANOMALY_DETECTION_BAND(m1, 2)',  # 2 std deviations
                    'Label': 'Throughput (expected)'
                }
            ],
            EvaluationPeriods=3,  # Check over 3 periods (15 minutes)
            DatapointsToAlarm=2,  # Must breach for 2 out of 3 periods
            ComparisonOperator='LessThanLowerOrGreaterThanUpperThreshold',
            ThresholdMetricId='ad1',  # Compare against anomaly detection band
            TreatMissingData='notBreaching',  # Missing data = don't alarm
            AlarmActions=[alarm_topic_arn]
        )
        print(f"  ✓ Created Throughput alarm for {website_name}")
        
        print(f"✓ Successfully created all alarms for {website_name}")
        
        # Add widgets to dashboard
        add_dashboard_widgets(website_name, dashboard_name)
        
    except Exception as e:
        print(f"✗ Error creating alarms for {website_name}: {str(e)}")
        raise


def handle_website_removed(website_name):
    """
    Delete CloudWatch alarms for a removed website
    
    Removes all three alarms associated with the website:
    - Availability alarm
    - Latency alarm
    - Throughput alarm
    
    Also removes the website's widgets from the CloudWatch dashboard.
    """
    print(f"Deleting alarms for {website_name}")
    
    alarm_names = [
        f"{website_name}-Availability-Alarm",
        f"{website_name}-Latency-Alarm",
        f"{website_name}-Throughput-Alarm"
    ]
    
    try:
        cloudwatch.delete_alarms(AlarmNames=alarm_names)
        print(f"✓ Successfully deleted alarms for {website_name}")
        
        # Remove widgets from dashboard
        remove_dashboard_widgets(website_name, os.environ['DASHBOARD_NAME'])
        
    except Exception as e:
        print(f"✗ Error deleting alarms for {website_name}: {str(e)}")
        # Don't raise - deletion failures shouldn't block the stream processing
        # The alarms might already be deleted or never existed


def add_dashboard_widgets(website_name, dashboard_name):
    """
    Add monitoring widgets for a website to the CloudWatch dashboard
    
    Creates three widgets in a row:
    - Availability widget (graph showing uptime)
    - Latency widget (graph showing response time)
    - Throughput widget (graph showing data transfer rate)
    """
    print(f"Adding dashboard widgets for {website_name}")
    
    try:
        # Get current dashboard configuration
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        dashboard_body = json.loads(response['DashboardBody'])
        
        # Dashboard uses a widgets array
        widgets = dashboard_body.get('widgets', [])
        
        # Calculate position for new widgets
        # Find the maximum Y coordinate to place new widgets below existing ones
        max_y = 0
        for widget in widgets:
            widget_y = widget.get('y', 0)
            widget_height = widget.get('height', 6)
            bottom = widget_y + widget_height
            if bottom > max_y:
                max_y = bottom
        
        # Create widget definitions for the new website
        # Place them in a row: Availability (col 0), Latency (col 6), Throughput (col 12)
        new_widgets = [
            {
                "type": "metric",
                "x": 0,
                "y": max_y,
                "width": 6,
                "height": 6,
                "properties": {
                    "metrics": [
                        [METRIC_NAMESPACE, METRIC_AVAILABILITY, DIM_WEBSITE, website_name]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": os.environ.get('DASHBOARD_REGION', 'ap-southeast-2'),
                    "title": f"{website_name} - Availability",
                    "yAxis": {
                        "left": {
                            "min": 0,
                            "max": 1.1
                        }
                    }
                }
            },
            {
                "type": "metric",
                "x": 6,
                "y": max_y,
                "width": 6,
                "height": 6,
                "properties": {
                    "metrics": [
                        [METRIC_NAMESPACE, METRIC_LATENCY, DIM_WEBSITE, website_name]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": os.environ.get('DASHBOARD_REGION', 'ap-southeast-2'),
                    "title": f"{website_name} - Latency (ms)",
                    "yAxis": {
                        "left": {
                            "min": 0
                        }
                    }
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": max_y,
                "width": 6,
                "height": 6,
                "properties": {
                    "metrics": [
                        [METRIC_NAMESPACE, METRIC_THROUGHPUT, DIM_WEBSITE, website_name]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": os.environ.get('DASHBOARD_REGION', 'ap-southeast-2'),
                    "title": f"{website_name} - Throughput (bytes/s)",
                    "yAxis": {
                        "left": {
                            "min": 0
                        }
                    }
                }
            }
        ]
        
        # Add new widgets to the dashboard
        widgets.extend(new_widgets)
        dashboard_body['widgets'] = widgets
        
        # Update the dashboard
        cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )
        
        print(f"  ✓ Added {len(new_widgets)} widgets to dashboard for {website_name}")
        
    except cloudwatch.exceptions.ResourceNotFound:
        print(f"  ⚠ Dashboard '{dashboard_name}' not found - skipping widget creation")
    except Exception as e:
        print(f"  ✗ Error adding dashboard widgets for {website_name}: {str(e)}")
        # Don't raise - dashboard updates are not critical


def remove_dashboard_widgets(website_name, dashboard_name):
    """
    Remove monitoring widgets for a website from the CloudWatch dashboard
    
    Removes all widgets that reference the specified website name in their title.
    """
    print(f"Removing dashboard widgets for {website_name}")
    
    try:
        # Get current dashboard configuration
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        dashboard_body = json.loads(response['DashboardBody'])
        
        # Dashboard uses a widgets array
        widgets = dashboard_body.get('widgets', [])
        original_count = len(widgets)
        
        # Filter out widgets that contain the website name in their title
        # This removes all three widgets (availability, latency, throughput) for this site
        filtered_widgets = [
            widget for widget in widgets
            if not (
                widget.get('properties', {}).get('title', '').startswith(f"{website_name} -")
            )
        ]
        
        removed_count = original_count - len(filtered_widgets)
        
        if removed_count > 0:
            # Update the dashboard with filtered widgets
            dashboard_body['widgets'] = filtered_widgets
            cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            print(f"  ✓ Removed {removed_count} widgets from dashboard for {website_name}")
        else:
            print(f"  ℹ No widgets found for {website_name}")
        
    except cloudwatch.exceptions.ResourceNotFound:
        print(f"  ⚠ Dashboard '{dashboard_name}' not found - skipping widget removal")
    except Exception as e:
        print(f"  ✗ Error removing dashboard widgets for {website_name}: {str(e)}")
        # Don't raise - dashboard updates are not critical