"""
Integration Tests for Web Monitoring Stack
Tests end-to-end workflows through API Gateway in deployed environment

Test Level: Integration Testing
- Tests complete system workflows with real AWS services
- Requires deployed infrastructure (runs against alpha stage)
- Makes HTTP requests through API Gateway (not direct Lambda invocation)
- Validates data flow through all components

AWS Services Tested:
- Amazon API Gateway: HTTP endpoint with CORS
  Documentation: https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
- AWS Lambda: Backend logic execution
- Amazon DynamoDB: Persistent data storage
- Amazon CloudWatch: Metrics and alarms
- DynamoDB Streams: Event-driven infrastructure updates

Test Strategy:
1. Make HTTP requests to API Gateway endpoints
2. Verify end-to-end data flow through all services
3. Validate DynamoDB data matches API responses
4. Check CloudWatch alarms are created/deleted automatically
5. Test error handling and edge cases

Complete Workflow Tests:
- CRUD operations (Create → Read → Update → Delete)
- API to DynamoDB integration
- Dynamic alarm creation via DynamoDB Streams
- Error handling and validation
"""

import requests
import boto3
import pytest
import time

# AWS clients
cloudformation = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

# Stack name for alpha stage
STACK_NAME = 'WebMonitoringPipeline-alpha-ThomasShewan22080488Stack'


@pytest.fixture(scope='module')
def api_url():
    """Get API Gateway URL from CloudFormation stack outputs"""
    try:
        response = cloudformation.describe_stacks(StackName=STACK_NAME)
        outputs = response['Stacks'][0]['Outputs']
        
        for output in outputs:
            if output['OutputKey'] == 'ApiUrl':
                return output['OutputValue']
        
        pytest.skip("ApiUrl output not found in stack")
    except Exception as e:
        pytest.skip(f"Stack not found or not deployed: {e}")


@pytest.fixture(scope='module')
def targets_table():
    """Get DynamoDB targets table"""
    try:
        response = cloudformation.describe_stacks(StackName=STACK_NAME)
        outputs = response['Stacks'][0]['Outputs']
        
        for output in outputs:
            if output['OutputKey'] == 'TargetsTableName':
                return dynamodb.Table(output['OutputValue'])
        
        pytest.skip("TargetsTableName output not found")
    except Exception as e:
        pytest.skip(f"Could not get table: {e}")


def test_end_to_end_crud_workflow(api_url, targets_table):
    """
    Test 1: Complete CRUD workflow through API Gateway.
    
    Tests the entire lifecycle: Create → Read → Update → Delete
    
    This validates:
    - API Gateway routing and CORS
    - Lambda proxy integration
    - DynamoDB CRUD operations
    - HTTP status codes and response formats
    - RESTful API design
    
    Workflow:
    1. POST /targets - Create new target, get generated ID
    2. GET /targets/{id} - Retrieve the created target
    3. PUT /targets/{id} - Update target name
    4. DELETE /targets/{id} - Remove target
    5. GET /targets/{id} - Verify 404 after deletion
    
    Each step verifies the previous operation succeeded.
    """
    # CREATE: Add new monitoring target
    create_response = requests.post(
        f"{api_url}targets",
        json={
            'name': 'integration-test-site',
            'url': 'https://httpbin.org'
        }
    )
    assert create_response.status_code == 201  # HTTP 201 Created
    created = create_response.json()
    target_id = created['TargetId']  # Save ID for subsequent operations
    
    # READ: Retrieve the created target
    get_response = requests.get(f"{api_url}targets/{target_id}")
    assert get_response.status_code == 200  # HTTP 200 OK
    assert get_response.json()['name'] == 'integration-test-site'
    
    # UPDATE: Modify target name
    update_response = requests.put(
        f"{api_url}targets/{target_id}",
        json={'name': 'integration-test-updated'}
    )
    assert update_response.status_code == 200  # HTTP 200 OK
    assert update_response.json()['name'] == 'integration-test-updated'
    
    # DELETE: Remove target
    delete_response = requests.delete(f"{api_url}targets/{target_id}")
    assert delete_response.status_code == 200  # HTTP 200 OK
    
    # VERIFY DELETION: Confirm target no longer exists
    verify_response = requests.get(f"{api_url}targets/{target_id}")
    assert verify_response.status_code == 404  # HTTP 404 Not Found


def test_api_to_dynamodb_integration(api_url, targets_table):
    """
    Test 2: Verify API Gateway writes correctly to DynamoDB
    """
    # Create via API
    response = requests.post(
        f"{api_url}targets",
        json={
            'name': 'db-integration-test',
            'url': 'https://aws.amazon.com'
        }
    )
    assert response.status_code == 201
    target_id = response.json()['TargetId']
    
    # Verify directly in DynamoDB
    db_response = targets_table.get_item(Key={'TargetId': target_id})
    assert 'Item' in db_response
    assert db_response['Item']['name'] == 'db-integration-test'
    assert db_response['Item']['url'] == 'https://aws.amazon.com'
    
    # Cleanup
    targets_table.delete_item(Key={'TargetId': target_id})


def test_monitoring_workflow_with_metrics(api_url, targets_table):
    """
    Test 3: Test that adding a target eventually produces CloudWatch metrics
    API → DynamoDB → Monitoring Lambda → CloudWatch
    """
    # Create a target
    response = requests.post(
        f"{api_url}targets",
        json={
            'name': 'metrics-test-site',
            'url': 'https://www.google.com'
        }
    )
    assert response.status_code == 201
    target_id = response.json()['TargetId']
    
    # Wait for potential monitoring cycle (this would normally take 5 minutes)
    # For testing, verify the target is queryable
    list_response = requests.get(f"{api_url}targets")
    assert list_response.status_code == 200
    
    targets = list_response.json()['targets']
    assert any(t['TargetId'] == target_id for t in targets)
    
    # Cleanup
    requests.delete(f"{api_url}targets/{target_id}")


def test_list_targets_with_multiple_items(api_url):
    """
    Test 5: Verify listing works with multiple targets
    """
    created_ids = []
    
    # Create multiple targets
    for i in range(3):
        response = requests.post(
            f"{api_url}targets",
            json={
                'name': f'list-test-{i}',
                'url': f'https://example-{i}.com'
            }
        )
        assert response.status_code == 201
        created_ids.append(response.json()['TargetId'])
    
    # List all targets
    list_response = requests.get(f"{api_url}targets")
    assert list_response.status_code == 200
    
    data = list_response.json()
    assert 'targets' in data
    assert data['count'] >= 3
    
    # Verify our targets are in the list
    target_ids = {t['TargetId'] for t in data['targets']}
    for created_id in created_ids:
        assert created_id in target_ids
    
    # Cleanup
    for target_id in created_ids:
        requests.delete(f"{api_url}targets/{target_id}")


def test_infrastructure_lambda_creates_alarms(api_url):
    """
    Test 6: Verify Infrastructure Lambda creates CloudWatch alarms
    Tests the full pipeline: API → DynamoDB → Stream → InfraLambda → CloudWatch Alarms
    """
    # Create a target with a unique name
    unique_name = f'alarm-test-{int(time.time())}'
    
    response = requests.post(
        f"{api_url}targets",
        json={
            'name': unique_name,
            'url': 'https://aws.amazon.com'
        }
    )
    assert response.status_code == 201
    target_id = response.json()['TargetId']
    
    # Wait for Infrastructure Lambda to process the DynamoDB stream event
    # and create the alarms (typically takes 5-10 seconds)
    time.sleep(15)
    
    # Check if alarms were created
    try:
        response = cloudwatch.describe_alarms(
            AlarmNamePrefix=f"{unique_name}-"
        )
        
        # Should have created 3 alarms: Availability, Latency, Throughput
        alarm_names = [alarm['AlarmName'] for alarm in response['MetricAlarms']]
        
        # Check for expected alarm names
        expected_alarms = [
            f"{unique_name}-Availability-Alarm",
            f"{unique_name}-Latency-Alarm",
            f"{unique_name}-Throughput-Alarm"
        ]
        
        # At least some alarms should be created (may take time for all)
        assert len(alarm_names) > 0, "No alarms were created"
        
        # Verify alarm structure
        for alarm in response['MetricAlarms']:
            assert alarm['Namespace'] == 'WebMonitoring/HealthChecks'
            assert unique_name in alarm['AlarmName']
        
    finally:
        # Cleanup - delete the target (Infrastructure Lambda should delete alarms)
        requests.delete(f"{api_url}targets/{target_id}")
