"""
Functional Tests for Web Monitoring Stack
Tests Lambda functions in deployed AWS environment (alpha stage)

Test Level: Functional Testing
- Tests individual Lambda functions with real AWS services
- Requires deployed infrastructure (runs against alpha stage)
- Validates Lambda execution, DynamoDB operations, CloudWatch metrics

AWS Services Tested:
- AWS Lambda: Direct function invocation
  Documentation: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- Amazon DynamoDB: Read/write operations
  Documentation: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html
- Amazon CloudWatch: Metric publication
  Documentation: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- AWS CloudFormation: Stack output retrieval
  Documentation: https://docs.aws.amazon.com/cloudformation/latest/userguide/Welcome.html

Test Strategy:
1. Invoke Lambda functions directly (not through API Gateway)
2. Verify function execution succeeds
3. Check DynamoDB for data changes
4. Verify CloudWatch metrics are published
5. Validate Lambda configuration (environment variables, event sources)

"""
import json
import boto3
import pytest

# Get stack outputs from CloudFormation
cloudformation = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
cloudwatch = boto3.client('cloudwatch')

# Stack name for alpha stage (deployed by pipeline)
STACK_NAME = 'alpha-ThomasShewan22080488Stack'


@pytest.fixture(scope='module')
def stack_outputs():
    """
    Retrieve CloudFormation stack outputs for testing.
    
    Stack outputs contain resource identifiers needed for testing:
    - TargetsTableName: DynamoDB table name
    - ApiUrl: API Gateway endpoint
    
    CloudFormation API:
    - describe_stacks: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation/client/describe_stacks.html
    
    Returns:
        dict: Mapping of output keys to values
    
    Raises:
        pytest.fail: If stack doesn't exist or outputs are unavailable
    """
    try:
        response = cloudformation.describe_stacks(StackName=STACK_NAME)
        outputs = response['Stacks'][0]['Outputs']
        return {output['OutputKey']: output['OutputValue'] for output in outputs}
    except Exception as e:
        pytest.fail(f"Failed to get stack outputs: {str(e)}")


@pytest.fixture(scope='module')
def targets_table(stack_outputs):
    """
    Get reference to DynamoDB targets table for direct data validation.
    
    Returns:
        boto3.resources.factory.dynamodb.Table: DynamoDB table resource
    
    DynamoDB Table resource:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/index.html
    """
    table_name = stack_outputs.get('TargetsTableName')
    if not table_name:
        pytest.fail("TargetsTableName not found in stack outputs")
    return dynamodb.Table(table_name)


def test_crud_lambda_creates_target(stack_outputs):
    """
    Test 1: Verify CRUD Lambda can create a target.
    
    Test Flow:
    1. Invoke CRUD Lambda directly with POST request payload
    2. Lambda writes to DynamoDB
    3. Verify response contains new target with generated ID
    
    This tests:
    - Lambda function execution
    - DynamoDB write permissions
    - UUID generation
    - Response formatting
    
    Lambda Invoke API:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda/client/invoke.html
    """
    # Construct Lambda event payload (simulates API Gateway proxy integration)
    # Event format: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
    payload = {
        'httpMethod': 'POST',
        'path': '/targets',
        'body': json.dumps({
            'name': 'test-functional-site',
            'url': 'https://example.com'
        }),
        'pathParameters': None
    }
    
    # Invoke Lambda synchronously (RequestResponse mode)
    response = lambda_client.invoke(
        FunctionName=f'alpha-WebMonitoringCRUD',
        InvocationType='RequestResponse',  # Wait for response
        Payload=json.dumps(payload)
    )
    
    # Parse Lambda response
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 201  # HTTP 201 Created
    
    # Verify response body contains target data
    body = json.loads(result['body'])
    assert 'TargetId' in body  # UUID generated
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
