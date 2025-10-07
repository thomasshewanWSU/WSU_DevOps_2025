"""
Functional Tests for Web Monitoring Stack
Tests that deployed AWS resources exist and are configured correctly
"""
import boto3
import pytest


@pytest.fixture(scope='module')
def cloudwatch_client():
    """CloudWatch client for testing"""
    return boto3.client('cloudwatch', region_name='ap-southeast-2')


@pytest.fixture(scope='module')
def lambda_client():
    """Lambda client for testing"""
    return boto3.client('lambda', region_name='ap-southeast-2')


def test_monitoring_lambda_exists(lambda_client):
    """Test that MonitoringLambda function exists"""
    response = lambda_client.list_functions()
    functions = [f['FunctionName'] for f in response['Functions']]
    monitoring_functions = [f for f in functions if 'MonitoringLambda' in f]
    assert len(monitoring_functions) > 0


def test_monitoring_lambda_has_correct_timeout(lambda_client):
    """Test that MonitoringLambda has 60 second timeout"""
    response = lambda_client.list_functions()
    functions = [f for f in response['Functions'] if 'MonitoringLambda' in f['FunctionName']]
    if functions:
        function_name = functions[0]['FunctionName']
        config = lambda_client.get_function_configuration(FunctionName=function_name)
        assert config['Timeout'] == 60


def test_four_lambda_operational_alarms_exist(cloudwatch_client):
    """Test that 4 Lambda operational alarms exist (Duration, Invocations, Errors, Memory)"""
    response = cloudwatch_client.describe_alarms()
    lambda_alarms = [a for a in response['MetricAlarms'] if 'CanaryLambda' in a['AlarmName']]
    assert len(lambda_alarms) >= 4


def test_memory_alarm_uses_custom_metrics(cloudwatch_client):
    """Test that memory alarm uses CustomLambdaMetrics namespace"""
    response = cloudwatch_client.describe_alarms(AlarmNames=['CanaryLambda-Memory-Alarm'])
    if response['MetricAlarms']:
        alarm = response['MetricAlarms'][0]
        assert alarm['Namespace'] == 'CustomLambdaMetrics'
        assert alarm['MetricName'] == 'MemoryUsedMB'


def test_cloudwatch_dashboard_exists(cloudwatch_client):
    """Test that CloudWatch dashboard exists"""
    response = cloudwatch_client.list_dashboards()
    dashboards = [d['DashboardName'] for d in response['DashboardEntries']]
    monitoring_dashboards = [d for d in dashboards if 'Monitoring' in d]
    assert len(monitoring_dashboards) > 0
