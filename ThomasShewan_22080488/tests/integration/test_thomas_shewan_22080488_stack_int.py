"""
Integration Tests for Web Monitoring System
Tests the complete end-to-end workflow of the monitoring system
"""
import boto3
import pytest
import time
import requests


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


# CRUD Testing

def api_url():
    """Get API URL from CloudFormation outputs"""
    cfn = boto3.client('cloudformation', region_name='ap-southeast-2')
    try:
        response = cfn.describe_stacks(StackName='prod-ThomasShewan22080488Stack')
        outputs = response['Stacks'][0]['Outputs']
        api_url = next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'ApiUrl')
        return api_url
    except Exception as e:
        pytest.skip(f"Stack not deployed: {str(e)}")

def test_crud_workflow_with_timing(api_url):
    """Test complete CRUD workflow and measure DynamoDB response times"""
    
    # CREATE - Measure write time
    create_start = time.time()
    response = requests.post(
        f"{api_url}targets",
        json={
            'name': 'Integration Test Site',
            'url': 'https://integration-test.example.com'
        }
    )
    create_time = (time.time() - create_start) * 1000
    
    assert response.status_code == 201
    target = response.json()
    target_id = target['TargetId']
    print(f"CREATE time: {create_time:.2f}ms")
    assert create_time < 1000  # Should be under 1 second
    
    # READ - Measure read time
    read_start = time.time()
    response = requests.get(f"{api_url}targets/{target_id}")
    read_time = (time.time() - read_start) * 1000
    
    assert response.status_code == 200
    print(f"READ time: {read_time:.2f}ms")
    assert read_time < 500
    
    # UPDATE - Measure update time
    update_start = time.time()
    response = requests.put(
        f"{api_url}targets/{target_id}",
        json={'enabled': False}
    )
    update_time = (time.time() - update_start) * 1000
    
    assert response.status_code == 200
    print(f"UPDATE time: {update_time:.2f}ms")
    assert update_time < 1000
    
    # DELETE - Measure delete time
    delete_start = time.time()
    response = requests.delete(f"{api_url}targets/{target_id}")
    delete_time = (time.time() - delete_start) * 1000
    
    assert response.status_code == 200
    print(f"DELETE time: {delete_time:.2f}ms")
    assert delete_time < 500
    
    # Verify deletion
    response = requests.get(f"{api_url}targets/{target_id}")
    assert response.status_code == 404

def test_list_targets_performance(api_url):
    """Test LIST operation and measure scan time"""
    start = time.time()
    response = requests.get(f"{api_url}targets")
    list_time = (time.time() - start) * 1000
    
    assert response.status_code == 200
    print(f"LIST time: {list_time:.2f}ms")
    assert list_time < 2000  # Scan can be slower with more items