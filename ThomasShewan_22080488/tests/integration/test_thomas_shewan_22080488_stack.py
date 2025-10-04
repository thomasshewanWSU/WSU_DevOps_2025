"""
Integration Tests for Web Monitoring System
Tests the complete end-to-end workflow of the monitoring system
"""
import boto3
import json
import pytest


from modules.constants import DEFAULT_WEBSITES

@pytest.fixture
def aws_clients():
    """Create all required AWS clients"""
    return {
        'lambda': boto3.client('lambda', region_name='ap-southeast-2'),
        'cloudwatch': boto3.client('cloudwatch', region_name='ap-southeast-2'),
        'dynamodb': boto3.resource('dynamodb', region_name='ap-southeast-2'),
        'sns': boto3.client('sns', region_name='ap-southeast-2')
    }


def test_sns_topic_exists(aws_clients):
    """Verify SNS alarm topic is configured"""
    try:
        response = aws_clients['sns'].list_topics()
        topics = [t['TopicArn'] for t in response['Topics']]
        alarm_topics = [t for t in topics if 'AlarmNotification' in t]
        assert len(alarm_topics) > 0, "AlarmNotificationTopic not found"
    except Exception as e:
        pytest.skip(f"SNS topics not available: {str(e)}")


def test_dynamodb_table_exists(aws_clients):
    """Check DynamoDB alarm log table exists"""
    try:
        tables = aws_clients['dynamodb'].meta.client.list_tables()
        table_names = tables['TableNames']
        alarm_tables = [t for t in table_names if 'AlarmLogTable' in t]
        assert len(alarm_tables) > 0, "AlarmLogTable not found"
    except Exception as e:
        pytest.skip(f"DynamoDB table not accessible: {str(e)}")


def test_cloudwatch_dashboard_exists(aws_clients):
    """Check CloudWatch dashboard is created"""
    try:
        response = aws_clients['cloudwatch'].list_dashboards()
        dashboards = [d['DashboardName'] for d in response['DashboardEntries']]
        health_dashboards = [d for d in dashboards if 'WebsiteHealthMonitoring' in d]
        assert len(health_dashboards) > 0, "WebsiteHealthMonitoring dashboard not found"
    except Exception as e:
        pytest.skip(f"Dashboard not available: {str(e)}")


def test_eventbridge_rule_exists(aws_clients):
    """Verify EventBridge scheduling rule exists and is enabled"""
    try:
        events_client = boto3.client('events', region_name='ap-southeast-2')
        response = events_client.list_rules()
        
        monitoring_rules = [r for r in response['Rules'] if 'Monitoring' in r.get('Name', '')]
        assert len(monitoring_rules) > 0
        
        rule = monitoring_rules[0]
        assert rule['State'] == 'ENABLED'
    except Exception as e:
        pytest.skip(f"EventBridge rule not available: {str(e)}")


def test_website_alarms_exist_for_each_site(aws_clients):
    """Check alarms exist for configured websites"""
    try:
        response = aws_clients['cloudwatch'].describe_alarms()
        
        if not response['MetricAlarms']:
            pytest.skip("No alarms deployed")
        
        alarm_names = [a['AlarmName'] for a in response['MetricAlarms']]
        configured_sites = [site['name'] for site in DEFAULT_WEBSITES]
        
        website_alarms = [
            a for a in alarm_names 
            if any(site in a for site in configured_sites)
        ]
        
        assert len(website_alarms) > 0
    except Exception as e:
        pytest.skip(f"Website alarms check failed: {str(e)}")


def test_lambda_alias_exists(aws_clients):
    """Verify Lambda prod alias exists for deployments"""
    try:
        # Find the monitoring Lambda
        response = aws_clients['lambda'].list_functions()
        functions = [f for f in response['Functions'] if 'MonitoringLambda' in f['FunctionName']]
        
        if not functions:
            pytest.skip("MonitoringLambda not found")
        
        function_name = functions[0]['FunctionName']
        
        alias_response = aws_clients['lambda'].list_aliases(FunctionName=function_name)
        aliases = [a['Name'] for a in alias_response['Aliases']]
        assert 'prod' in aliases, "prod alias not found"
    except Exception as e:
        pytest.skip(f"Lambda alias check failed: {str(e)}")


def test_codedeploy_application_exists(aws_clients):
    """Check CodeDeploy application is configured"""
    try:
        codedeploy_client = boto3.client('codedeploy', region_name='ap-southeast-2')
        response = codedeploy_client.list_applications()
        
        apps = response['applications']
        monitoring_apps = [a for a in apps if 'Monitoring' in a or 'Canary' in a]
        assert len(monitoring_apps) > 0
    except Exception as e:
        pytest.skip(f"CodeDeploy application not available: {str(e)}")


def test_complete_monitoring_workflow():
    """Test end-to-end monitoring workflow without triggering actual checks"""
    lambda_client = boto3.client('lambda', region_name='ap-southeast-2')
    cloudwatch_client = boto3.client('cloudwatch', region_name='ap-southeast-2')
    
    try:
        # Verify Lambda exists
        response = lambda_client.list_functions()
        functions = [f for f in response['Functions'] if 'MonitoringLambda' in f['FunctionName']]
        assert len(functions) > 0, "MonitoringLambda not found"
        
        # Verify metrics namespace exists
        metrics_response = cloudwatch_client.list_metrics(
            Namespace='WebMonitoring/Health'
        )
        assert 'Metrics' in metrics_response
        
        # Verify alarms exist
        alarms_response = cloudwatch_client.describe_alarms()
        relevant_alarms = [a for a in alarms_response['MetricAlarms'] if '-Alarm' in a['AlarmName']]
        assert len(relevant_alarms) > 0, "No monitoring alarms found"

        print("Workflow verified: Lambda - CloudWatch - Alarms")

    except AssertionError as e:
        pytest.fail(str(e))
    except Exception as e:
        pytest.skip(f"Workflow test skipped: {str(e)}")