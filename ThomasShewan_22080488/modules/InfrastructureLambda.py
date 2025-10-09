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

# Initialize CloudWatch client for alarm and dashboard management
# CloudWatch Client API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch.html
cloudwatch = boto3.client('cloudwatch')


def lambda_handler(event, context):
    """
    Process DynamoDB stream events and manage CloudWatch monitoring infrastructure.
    
    This Lambda is triggered automatically by DynamoDB Streams when the targets table changes.
    It implements event-driven infrastructure management:
    - INSERT events → Create new CloudWatch alarms for the website
    - REMOVE events → Delete CloudWatch alarms for the website
    - MODIFY events → Recreate alarms if website name changed
    """
    # Get configuration from environment variables 
    # Environment variables documentation: https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
    alarm_topic_arn = os.environ['ALARM_TOPIC_ARN']  # SNS topic for alarm actions
    dashboard_name = os.environ['DASHBOARD_NAME']    # Dashboard to update with widgets
    
    # Process each DynamoDB stream record
    # Records are batched by Lambda (configured via batch_size in CDK stack)
    # DynamoDB Streams record format: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.Lambda.Tutorial.html
    for record in event['Records']:
        event_name = record['eventName']  # Type of DynamoDB operation
        
        try:
            if event_name == 'INSERT':
                # INSERT EVENT: New website added via CRUD API
                # Create CloudWatch alarms and add to dashboard
                # NewImage contains the full item after the INSERT operation
                # DynamoDB JSON format documentation: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.LowLevelAPI.html#Programming.LowLevelAPI.DataTypeDescriptors
                new_image = record['dynamodb']['NewImage']
                # Extract website name from DynamoDB JSON format
                # Format: {'name': {'S': 'actual_string_value'}}
                website_name = new_image['name']['S']
                print(f"Processing INSERT event for website: {website_name}")
                handle_website_added(website_name, alarm_topic_arn, dashboard_name)
                
            elif event_name == 'REMOVE':
                # REMOVE EVENT: Website deleted via CRUD API
                # Delete CloudWatch alarms and remove from dashboard
                # OldImage contains the full item before the DELETE operation
                old_image = record['dynamodb']['OldImage']
                website_name = old_image['name']['S']
                print(f"Processing REMOVE event for website: {website_name}")
                handle_website_removed(website_name)
                
            elif event_name == 'MODIFY':
                # MODIFY EVENT: Website updated via CRUD API
                # Check if the website name changed (alarms are keyed by name)
                # Both OldImage and NewImage are available for MODIFY events
                old_image = record['dynamodb']['OldImage']
                new_image = record['dynamodb']['NewImage']
                old_name = old_image['name']['S']
                new_name = new_image['name']['S']
                
                if old_name != new_name:
                    # Website renamed - need to recreate alarms with new name
                    # CloudWatch alarm names are immutable, so we delete old and create new
                    print(f"Processing MODIFY event: {old_name} -> {new_name}")
                    handle_website_removed(old_name)
                    handle_website_added(new_name, alarm_topic_arn, dashboard_name)
                else:
                    # Other fields changed (URL, enabled status, etc.) but not name
                    # No action needed as alarms are based on metrics by website name
                    print(f"Website {new_name} modified but name unchanged - no action needed")
                    
        except Exception as e:
            # Log error but continue processing remaining records
            # One failed record shouldn't block infrastructure updates for other websites
            print(f"Error processing record: {str(e)}")
            print(f"Record: {json.dumps(record)}")
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
        # PutMetricAlarm API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/put_metric_alarm.html
        cloudwatch.put_metric_alarm(
            AlarmName=f"{website_name}-Availability-Alarm",
            AlarmDescription=f"Alert when {website_name} is unavailable",
            MetricName=METRIC_AVAILABILITY,
            Namespace=METRIC_NAMESPACE,
            Statistic='Average',  # Average of availability metrics (0 or 1)
            Dimensions=[{'Name': DIM_WEBSITE, 'Value': website_name}],
            Period=300,  # 5 minutes (matches monitoring Lambda schedule)
            EvaluationPeriods=2,  # Check over 2 periods (10 minutes total)
            DatapointsToAlarm=2,  # Must breach threshold for both periods 
            Threshold=1.0,  # Alert when < 1 (site is down)
            ComparisonOperator='LessThanThreshold',
            TreatMissingData='breaching',  # Missing data means monitoring failed = alarm
            AlarmActions=[alarm_topic_arn]  # Send notification to SNS topic
        )
        print(f"Created Availability alarm for {website_name}")
        
        # Create Latency Alarm (with anomaly detection)
        # Alerts when response time deviates from normal patterns
        # Uses CloudWatch Anomaly Detection for dynamic thresholds
        # Anomaly Detection guide: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Anomaly_Detection_Alarm.html
        cloudwatch.put_metric_alarm(
            AlarmName=f"{website_name}-Latency-Alarm",
            AlarmDescription=f"Alert when {website_name} latency is anomalous (outside 4 standard deviations)",
            Metrics=[
                {
                    'Id': 'm1',  # Metric identifier for the actual latency metric
                    'ReturnData': True,  # Return this metric value in alarm evaluation
                    'MetricStat': {
                        'Metric': {
                            'Namespace': METRIC_NAMESPACE,
                            'MetricName': METRIC_LATENCY,
                            'Dimensions': [{'Name': DIM_WEBSITE, 'Value': website_name}]
                        },
                        'Period': 300,  # 5 minutes
                        'Stat': 'Average'  # Average response time
                    }
                },
                {
                    'Id': 'ad1',  # Anomaly detection band identifier
                    'Expression': 'ANOMALY_DETECTION_BAND(m1, 4)',  # 4 std deviations from learned baseline (more tolerant)
                    'Label': 'Latency (expected)'
                }
            ],
            EvaluationPeriods=4,  # Check over 4 periods (20 minutes)
            DatapointsToAlarm=3,  # Must breach for 3 out of 4 periods (M out of N) - more tolerant
            ComparisonOperator='LessThanLowerOrGreaterThanUpperThreshold',  # Breach either bound
            ThresholdMetricId='ad1',  # Compare m1 against ad1 band
            TreatMissingData='notBreaching',  # Missing data = don't alarm (new site learning period)
            AlarmActions=[alarm_topic_arn]
        )
        print(f"Created Latency alarm for {website_name}")
        
        # Create Throughput Alarm (with anomaly detection)
        # Alerts when data transfer rate deviates from normal patterns
        # Detects both unusually high (potential DDoS) and low (content truncation) throughput
        cloudwatch.put_metric_alarm(
            AlarmName=f"{website_name}-Throughput-Alarm",
            AlarmDescription=f"Alert when {website_name} throughput is anomalous (outside 4 standard deviations)",
            Metrics=[
                {
                    'Id': 'm1',  # Metric identifier for the actual throughput metric
                    'ReturnData': True,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': METRIC_NAMESPACE,
                            'MetricName': METRIC_THROUGHPUT,
                            'Dimensions': [{'Name': DIM_WEBSITE, 'Value': website_name}]
                        },
                        'Period': 300,  # 5 minutes
                        'Stat': 'Average'  # Average bytes per second
                    }
                },
                {
                    'Id': 'ad1',  # Anomaly detection band identifier
                    'Expression': 'ANOMALY_DETECTION_BAND(m1, 4)',  # 4 std deviations from learned baseline (more tolerant)
                    'Label': 'Throughput (expected)'
                }
            ],
            EvaluationPeriods=4,  # Check over 4 periods (20 minutes)
            DatapointsToAlarm=3,  # Must breach for 3 out of 4 periods (M out of N) - more tolerant
            ComparisonOperator='LessThanLowerOrGreaterThanUpperThreshold',  # Breach either bound
            ThresholdMetricId='ad1',  # Compare m1 against ad1 band
            TreatMissingData='notBreaching',  # Missing data = don't alarm (new site learning period)
            AlarmActions=[alarm_topic_arn]
        )
        print(f"Created Throughput alarm for {website_name}")
        
        print(f"Successfully created all alarms for {website_name}")
        
        # Add widgets to dashboard
        add_dashboard_widgets(website_name, dashboard_name)
        
    except Exception as e:
        print(f"Error creating alarms for {website_name}: {str(e)}")
        raise


def handle_website_removed(website_name):
    """
    Delete CloudWatch alarms for a removed website
    
    Removes all three alarms associated with the website:
    - Availability alarm
    - Latency alarm
    - Throughput alarm
    
    Also removes the website's widgets from the CloudWatch dashboard.
    
    Args:
        website_name: Name of the website being removed from monitoring
    """
    print(f"Deleting alarms for {website_name}")
    
    # Construct alarm names using the same naming convention from handle_website_added()
    alarm_names = [
        f"{website_name}-Availability-Alarm",
        f"{website_name}-Latency-Alarm",
        f"{website_name}-Throughput-Alarm"
    ]
    
    try:
        # Delete all alarms in a single API call
        # DeleteAlarms API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/delete_alarms.html
        cloudwatch.delete_alarms(AlarmNames=alarm_names)
        print(f"Successfully deleted alarms for {website_name}")
        
        # Remove widgets from dashboard
        remove_dashboard_widgets(website_name, os.environ['DASHBOARD_NAME'])
        
    except Exception as e:
        print(f"Error deleting alarms for {website_name}: {str(e)}")
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
    
    Args:
        website_name: Name of the website to add to dashboard
        dashboard_name: CloudWatch dashboard name to update
    """
    print(f"Adding {website_name} to aggregate dashboard widgets")
    
    try:
        # Get current dashboard configuration
        # GetDashboard API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/get_dashboard.html
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        # Dashboard body is a JSON string that needs parsing
        # Dashboard body structure: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/CloudWatch-Dashboard-Body-Structure.html
        dashboard_body = json.loads(response['DashboardBody'])
        
        # Dashboard uses a widgets array containing all graph/text/number widgets
        widgets = dashboard_body.get('widgets', [])
        
        # Find the three aggregate widgets by title (created in CDK stack)
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
                
        if availability_widget:
            metrics = availability_widget['properties'].get('metrics', [])
            # Remove placeholder metrics (dimension value = "__placeholder__")
            # Placeholder is added by CDK when no real websites exist yet
            metrics = [m for m in metrics if not (len(m) >= 4 and m[3] == '__placeholder__')]
            # Add new metric line with explicit label
            # Metric array format: [Namespace, MetricName, DimensionName, DimensionValue, {options}]
            # CloudWatch metric format: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/CloudWatch-Dashboard-Body-Structure.html#CloudWatch-Dashboard-Properties-Metrics-Array-Format
            metrics.append([METRIC_NAMESPACE, METRIC_AVAILABILITY, DIM_WEBSITE, website_name, {"label": website_name}])
            availability_widget['properties']['metrics'] = metrics
            print(f"Added {website_name} to Availability widget")
        
        if latency_widget:
            metrics = latency_widget['properties'].get('metrics', [])
            # Remove placeholder metrics
            metrics = [m for m in metrics if not (len(m) >= 4 and m[3] == '__placeholder__')]
            metrics.append([METRIC_NAMESPACE, METRIC_LATENCY, DIM_WEBSITE, website_name, {"label": website_name}])
            latency_widget['properties']['metrics'] = metrics
            print(f"Added {website_name} to Latency widget")
        
        if throughput_widget:
            metrics = throughput_widget['properties'].get('metrics', [])
            # Remove placeholder metrics
            metrics = [m for m in metrics if not (len(m) >= 4 and m[3] == '__placeholder__')]
            metrics.append([METRIC_NAMESPACE, METRIC_THROUGHPUT, DIM_WEBSITE, website_name, {"label": website_name}])
            throughput_widget['properties']['metrics'] = metrics
            print(f"Added {website_name} to Throughput widget")
        
        # Update the dashboard with modified widgets
        # PutDashboard API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/put_dashboard.html
        cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)  # Convert back to JSON string
        )
        
        print(f"Successfully added {website_name} to aggregate dashboard")
        
    except cloudwatch.exceptions.ResourceNotFound:
        print(f"Dashboard '{dashboard_name}' not found - skipping widget updates")
    except Exception as e:
        print(f"Error updating dashboard for {website_name}: {str(e)}")
        # Don't raise - dashboard updates are not critical


def remove_dashboard_widgets(website_name, dashboard_name):
    """
    Remove a website's metrics from the aggregate dashboard widgets
    
    Removes the metric lines for this website from the 3 aggregate widgets.
    If no websites remain, adds a placeholder to keep the dashboard valid.
    
    Args:
        website_name: Name of the website to remove from dashboard
        dashboard_name: CloudWatch dashboard name to update
    """
    print(f"Removing {website_name} from aggregate dashboard widgets")
    
    try:
        # Get current dashboard configuration
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        dashboard_body = json.loads(response['DashboardBody'])
        
        # Dashboard uses a widgets array
        widgets = dashboard_body.get('widgets', [])
        
        # Track how many metrics were removed across all widgets
        removed_count = 0
        
        # Find and update the three aggregate widgets by scanning all widgets
        for widget in widgets:
            title = widget.get('properties', {}).get('title', '')
            
            # Check if this is one of our aggregate widgets
            if title in ['Website Availability (All Sites)', 
                        'Response Time - All Websites (ms)', 
                        'Throughput - All Websites (bytes/s)']:
                
                metrics = widget['properties'].get('metrics', [])
                original_count = len(metrics)
                
                # Filter out metrics for this website
                # Metric format: [Namespace, MetricName, DimensionName, DimensionValue, {...options}]
                # Match on the dimension value (4th element, index 3)
                filtered_metrics = [
                    metric for metric in metrics
                    if not (len(metric) >= 4 and metric[3] == website_name)
                ]
                
                # If we removed all real websites, add a placeholder to keep dashboard valid
                # Empty widgets cause dashboard rendering errors
                if len(filtered_metrics) == 0:
                    # Determine which metric type based on widget title
                    # This ensures the placeholder uses the correct metric name
                    if 'Availability' in title:
                        metric_name = METRIC_AVAILABILITY
                    elif 'Response Time' in title or 'Latency' in title:
                        metric_name = METRIC_LATENCY
                    else:  # Throughput
                        metric_name = METRIC_THROUGHPUT
                    
                    # Add placeholder metric with non-existent dimension value
                    # This prevents "No data" errors in the dashboard
                    filtered_metrics = [[METRIC_NAMESPACE, metric_name, DIM_WEBSITE, '__placeholder__']]
                    print(f"Added placeholder to '{title}' (no websites remaining)")
                
                if len(filtered_metrics) < original_count:
                    widget['properties']['metrics'] = filtered_metrics
                    removed_count += (original_count - len(filtered_metrics))
                    print(f"Removed {website_name} from '{title}'")
        
        if removed_count > 0:
            # Update the dashboard with filtered metrics
            # PutDashboard API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/put_dashboard.html
            cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)  # Convert back to JSON string
            )
            print(f"Successfully removed {website_name} from dashboard ({removed_count} metrics removed)")
        else:
            print(f"No metrics found for {website_name} in dashboard")
        
    except cloudwatch.exceptions.ResourceNotFound:
        print(f"Dashboard '{dashboard_name}' not found - skipping widget removal")
    except Exception as e:
        print(f"Error removing {website_name} from dashboard: {str(e)}")
        # Don't raise - dashboard updates are not critical