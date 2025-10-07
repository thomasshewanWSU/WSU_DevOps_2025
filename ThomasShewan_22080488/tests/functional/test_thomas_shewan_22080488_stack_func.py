"""
Functional Tests for Web Monitoring Stack
Tests Lambda functions in deployed AWS environment (alpha stage)

These tests verify that individual Lambda functions work correctly
when deployed to AWS with actual services (DynamoDB, CloudWatch, etc.)
"""
import json
import boto3
import pytest
from datetime import datetime

# Get stack outputs from CloudFormation
cloudformation = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
cloudwatch = boto3.client('cloudwatch')

# Stack name for alpha stage
STACK_NAME = 'WebMonitoringPipeline-alpha-ThomasShewan22080488Stack'


@pytest.fixture(scope='module')
def stack_outputs():
    """Retrieve CloudFormation stack outputs"""
    try:
        response = cloudformation.describe_stacks(StackName=STACK_NAME)
        outputs = response['Stacks'][0]['Outputs']
        return {output['OutputKey']: output['OutputValue'] for output in outputs}
    except Exception as e:
        pytest.skip(f"Stack not found or not deployed: {e}")


@pytest.fixture(scope='module')
def targets_table(stack_outputs):
    """Get DynamoDB targets table"""
    table_name = stack_outputs.get('TargetsTableName')
    if not table_name:
        pytest.skip("TargetsTableName output not found")
    return dynamodb.Table(table_name)


def test_crud_lambda_creates_target(stack_outputs):
    """
    Test 1: Verify CRUD Lambda can create a target
    Invokes the Lambda directly and checks DynamoDB
    """
    # Invoke CRUD Lambda with POST request
    payload = {
        'httpMethod': 'POST',
        'path': '/targets',
        'body': json.dumps({
            'name': 'test-functional-site',
            'url': 'https://example.com'
        }),
        'pathParameters': None
    }
    
    response = lambda_client.invoke(
        FunctionName=f'alpha-WebMonitoringCRUD',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 201
    
    body = json.loads(result['body'])
    assert 'TargetId' in body
    assert body['name'] == 'test-functional-site'
    assert body['url'] == 'https://example.com'


def test_crud_lambda_lists_targets(stack_outputs):
    """
    Test 2: Verify CRUD Lambda can list all targets
    """
    payload = {
        'httpMethod': 'GET',
        'path': '/targets',
        'pathParameters': None
    }
    
    response = lambda_client.invoke(
        FunctionName=f'alpha-WebMonitoringCRUD',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 200
    
    body = json.loads(result['body'])
    assert 'targets' in body
    assert 'count' in body
    assert isinstance(body['targets'], list)


def test_monitoring_lambda_executes(stack_outputs):
    """
    Test 3: Verify Monitoring Lambda executes without errors
    Checks that the Lambda runs and publishes metrics
    """
    response = lambda_client.invoke(
        FunctionName=f'alpha-WebMonitoring',
        InvocationType='RequestResponse',
        Payload=json.dumps({})
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 200
    
    body = json.loads(result['body'])
    assert 'message' in body
    assert 'monitored_count' in body


def test_monitoring_lambda_publishes_metrics(stack_outputs):
    """
    Test 4: Verify Monitoring Lambda publishes CloudWatch metrics
    """
    # Wait a moment for metrics to be published
    import time
    time.sleep(5)
    
    # Check if metrics exist in CloudWatch
    response = cloudwatch.list_metrics(
        Namespace='WebMonitoring/HealthChecks'
    )
    
    # Should have at least some metrics published
    assert len(response['Metrics']) > 0
    
    # Verify expected metric names
    metric_names = {metric['MetricName'] for metric in response['Metrics']}
    assert any(name in metric_names for name in ['Availability', 'Latency', 'Throughput'])


def test_alarm_logger_lambda_exists(stack_outputs):
    """
    Test 5: Verify Alarm Logger Lambda is deployed and configured
    """
    try:
        response = lambda_client.get_function(
            FunctionName='alpha-AlarmLogger'
        )
        
        # Check environment variables are set
        env_vars = response['Configuration']['Environment']['Variables']
        assert 'ALARM_LOG_TABLE' in env_vars
        assert env_vars['ALARM_LOG_TABLE'] == 'alpha-AlarmLog'
        
    except lambda_client.exceptions.ResourceNotFoundException:
        pytest.fail("AlarmLogger Lambda not found")


def test_infrastructure_lambda_exists(stack_outputs):
    """
    Test 6: Verify Infrastructure Lambda is deployed and configured
    Tests that the Infrastructure Lambda has proper environment variables
    """
    try:
        response = lambda_client.get_function(
            FunctionName='alpha-InfrastructureManager'
        )
        
        # Check environment variables are set
        env_vars = response['Configuration']['Environment']['Variables']
        assert 'ALARM_TOPIC_ARN' in env_vars
        assert 'DASHBOARD_NAME' in env_vars
        assert 'alpha' in env_vars['DASHBOARD_NAME'].lower()
        
    except lambda_client.exceptions.ResourceNotFoundException:
        pytest.fail("Infrastructure Lambda not found")


def test_infrastructure_lambda_has_stream_trigger(stack_outputs):
    """
    Test 7: Verify Infrastructure Lambda is triggered by DynamoDB stream
    Ensures the Lambda will automatically create/delete alarms when targets change
    """
    try:
        # Get Lambda event source mappings
        response = lambda_client.list_event_source_mappings(
            FunctionName='alpha-InfrastructureManager'
        )
        
        # Should have at least one event source mapping (DynamoDB stream)
        assert len(response['EventSourceMappings']) > 0
        
        # Verify it's a DynamoDB stream
        mapping = response['EventSourceMappings'][0]
        assert 'dynamodb' in mapping['EventSourceArn'].lower()
        assert mapping['State'] in ['Enabled', 'Enabling']
        
    except Exception as e:
        pytest.fail(f"Infrastructure Lambda stream trigger not configured: {e}")
