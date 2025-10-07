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
    Add a website's metrics to the aggregate dashboard widgets
    
    Instead of creating new widgets per site, this updates 3 existing aggregate widgets:
    - Availability widget (all websites as separate lines)
    - Latency widget (all websites as separate lines)
    - Throughput widget (all websites as separate lines)
    
    This approach scales much better - 100 websites = still just 3 widgets!
    """
    print(f"Adding {website_name} to aggregate dashboard widgets")
    
    try:
        # Get current dashboard configuration
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        dashboard_body = json.loads(response['DashboardBody'])
        
        # Dashboard uses a widgets array
        widgets = dashboard_body.get('widgets', [])
        
        # Find the three aggregate widgets by title
        availability_widget = None
        latency_widget = None
        throughput_widget = None
        
        for widget in widgets:
            title = widget.get('properties', {}).get('title', '')
            if title == 'Website Availability (All Sites)':
                availability_widget = widget
            elif title == 'Response Time - All Websites (ms)':
                latency_widget = widget
            elif title == 'Throughput - All Websites (bytes/s)':
                throughput_widget = widget
        
        # Add the new website's metric to each widget
        region = os.environ.get('DASHBOARD_REGION', 'ap-southeast-2')
        
        if availability_widget:
            metrics = availability_widget['properties'].get('metrics', [])
            # Remove placeholder metrics (dimension value = "__placeholder__")
            metrics = [m for m in metrics if not (len(m) >= 4 and m[3] == '__placeholder__')]
            # Add new metric line: [Namespace, MetricName, DimensionName, DimensionValue]
            metrics.append([METRIC_NAMESPACE, METRIC_AVAILABILITY, DIM_WEBSITE, website_name])
            availability_widget['properties']['metrics'] = metrics
            print(f"  ✓ Added {website_name} to Availability widget")
        
        if latency_widget:
            metrics = latency_widget['properties'].get('metrics', [])
            # Remove placeholder metrics
            metrics = [m for m in metrics if not (len(m) >= 4 and m[3] == '__placeholder__')]
            metrics.append([METRIC_NAMESPACE, METRIC_LATENCY, DIM_WEBSITE, website_name])
            latency_widget['properties']['metrics'] = metrics
            print(f"  ✓ Added {website_name} to Latency widget")
        
        if throughput_widget:
            metrics = throughput_widget['properties'].get('metrics', [])
            # Remove placeholder metrics
            metrics = [m for m in metrics if not (len(m) >= 4 and m[3] == '__placeholder__')]
            metrics.append([METRIC_NAMESPACE, METRIC_THROUGHPUT, DIM_WEBSITE, website_name])
            throughput_widget['properties']['metrics'] = metrics
            print(f"  ✓ Added {website_name} to Throughput widget")
        
        # Update the dashboard
        cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )
        
        print(f"✓ Successfully added {website_name} to aggregate dashboard")
        
    except cloudwatch.exceptions.ResourceNotFound:
        print(f"  ⚠ Dashboard '{dashboard_name}' not found - skipping widget updates")
    except Exception as e:
        print(f"  ✗ Error updating dashboard for {website_name}: {str(e)}")
        # Don't raise - dashboard updates are not critical


def remove_dashboard_widgets(website_name, dashboard_name):
    """
    Remove a website's metrics from the aggregate dashboard widgets
    
    Removes the metric lines for this website from the 3 aggregate widgets.
    """
    print(f"Removing {website_name} from aggregate dashboard widgets")
    
    try:
        # Get current dashboard configuration
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        dashboard_body = json.loads(response['DashboardBody'])
        
        # Dashboard uses a widgets array
        widgets = dashboard_body.get('widgets', [])
        
        # Track how many metrics were removed
        removed_count = 0
        
        # Find and update the three aggregate widgets
        for widget in widgets:
            title = widget.get('properties', {}).get('title', '')
            
            # Check if this is one of our aggregate widgets
            if title in ['Website Availability (All Sites)', 
                        'Response Time - All Websites (ms)', 
                        'Throughput - All Websites (bytes/s)']:
                
                metrics = widget['properties'].get('metrics', [])
                original_count = len(metrics)
                
                # Filter out metrics for this website
                # Metric format: [Namespace, MetricName, DimensionName, DimensionValue]
                filtered_metrics = [
                    metric for metric in metrics
                    if not (len(metric) >= 4 and metric[3] == website_name)
                ]
                
                # If we removed all real websites, add a placeholder to keep dashboard valid
                if len(filtered_metrics) == 0:
                    # Determine which metric type based on title
                    if 'Availability' in title:
                        metric_name = METRIC_AVAILABILITY
                    elif 'Response Time' in title or 'Latency' in title:
                        metric_name = METRIC_LATENCY
                    else:  # Throughput
                        metric_name = METRIC_THROUGHPUT
                    
                    filtered_metrics = [[METRIC_NAMESPACE, metric_name, DIM_WEBSITE, '__placeholder__']]
                    print(f"  ℹ Added placeholder to '{title}' (no websites remaining)")
                
                if len(filtered_metrics) < original_count:
                    widget['properties']['metrics'] = filtered_metrics
                    removed_count += (original_count - len(filtered_metrics))
                    print(f"  ✓ Removed {website_name} from '{title}'")
        
        if removed_count > 0:
            # Update the dashboard with filtered metrics
            cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            print(f"✓ Successfully removed {website_name} from dashboard ({removed_count} metrics removed)")
        else:
            print(f"  ℹ No metrics found for {website_name} in dashboard")
        
    except cloudwatch.exceptions.ResourceNotFound:
        print(f"  ⚠ Dashboard '{dashboard_name}' not found - skipping widget removal")
    except Exception as e:
        print(f"  ✗ Error removing {website_name} from dashboard: {str(e)}")
        # Don't raise - dashboard updates are not critical