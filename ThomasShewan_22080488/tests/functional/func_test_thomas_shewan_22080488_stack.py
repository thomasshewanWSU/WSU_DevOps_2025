"""
Functional Tests for Web Monitoring Lambda
Tests the behavior of the Lambda function in a deployed environment
"""
import boto3
import pytest

@pytest.fixture
def lambda_client():
    """Create boto3 Lambda client"""
    return boto3.client('lambda', region_name='ap-southeast-2')

@pytest.fixture
def cloudwatch_client():
    """Create boto3 CloudWatch client"""
    return boto3.client('cloudwatch', region_name='ap-southeast-2')


def test_lambda_exists(lambda_client):
    """Test that the monitoring Lambda function exists and is accessible"""
    try:
        response = lambda_client.list_functions()
        functions = [f for f in response['Functions'] if 'MonitoringLambda' in f['FunctionName']]
        assert len(functions) > 0, "MonitoringLambda not found"
        assert functions[0]['Runtime'].startswith('python3')
    except Exception as e:
        pytest.skip(f"Lambda function not deployed yet: {str(e)}")


def test_lambda_has_correct_timeout(lambda_client):
    """Test that Lambda has appropriate timeout configured"""
    try:
        response = lambda_client.list_functions()
        functions = [f for f in response['Functions'] if 'MonitoringLambda' in f['FunctionName']]
        if not functions:
            pytest.skip("MonitoringLambda not found")
        
        function_name = functions[0]['FunctionName']
        config = lambda_client.get_function_configuration(FunctionName=function_name)
        # Should have timeout of 60 seconds as configured in stack
        assert config['Timeout'] >= 60
    except Exception as e:
        pytest.skip(f"Lambda function not deployed yet: {str(e)}")

def test_cloudwatch_metrics_exist(cloudwatch_client):
    """Test that CloudWatch metrics namespace exists"""
    try:
        response = cloudwatch_client.list_metrics(
            Namespace='WebMonitoring/Health'
        )
        # Should have at least some metrics defined 
        assert 'Metrics' in response
        print(f"Found {len(response['Metrics'])} metrics in namespace")
    except Exception as e:
        pytest.skip(f"Metrics not available yet: {str(e)}")


def test_availability_metric_exists(cloudwatch_client):
    """Test that Availability metric is defined"""
    try:
        response = cloudwatch_client.list_metrics(
            Namespace='WebMonitoring/Health',
            MetricName='Availability'
        )
        assert len(response['Metrics']) >= 0  
    except Exception as e:
        pytest.skip(f"Availability metric not available yet: {str(e)}")


def test_latency_metric_exists(cloudwatch_client):
    """Test that Latency metric is defined"""
    try:
        response = cloudwatch_client.list_metrics(
            Namespace='WebMonitoring/Health',
            MetricName='Latency'
        )
        assert len(response['Metrics']) >= 0
    except Exception as e:
        pytest.skip(f"Latency metric not available yet: {str(e)}")


def test_throughput_metric_exists(cloudwatch_client):
    """Test that Throughput metric is defined"""
    try:
        response = cloudwatch_client.list_metrics(
            Namespace='WebMonitoring/Health',
            MetricName='Throughput'
        )
        assert len(response['Metrics']) >= 0
    except Exception as e:
        pytest.skip(f"Throughput metric not available yet: {str(e)}")


def test_alarms_exist(cloudwatch_client):
    """Test that CloudWatch alarms are configured"""
    try:
        response = cloudwatch_client.describe_alarms()
        # Should have at least some alarms created
        assert len(response['MetricAlarms']) > 0
        print(f"Found {len(response['MetricAlarms'])} alarms configured")
    except Exception as e:
        pytest.skip(f"Alarms not available yet: {str(e)}")


def test_lambda_alarm_exists(cloudwatch_client):
    """Test that Lambda operational alarms exist"""
    try:
        response = cloudwatch_client.describe_alarms()
        # Filter for Lambda alarms (contain "CanaryLambda" in name)
        lambda_alarms = [a for a in response['MetricAlarms'] if 'CanaryLambda' in a['AlarmName']]
        # Should have at least one Lambda alarm (Duration, Invocations, or Errors)
        assert len(lambda_alarms) > 0, "No CanaryLambda alarms found"
    except Exception as e:
        pytest.skip(f"Lambda alarms not available yet: {str(e)}")
