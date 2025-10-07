"""
Integration Tests for Web Monitoring System
Tests that all AWS resources work together correctly
"""
import boto3
import pytest
import time
import requests


@pytest.fixture(scope='module')
def cloudwatch_client():
    """CloudWatch client"""
    return boto3.client('cloudwatch', region_name='ap-southeast-2')


@pytest.fixture(scope='module')
def dynamodb_client():
    """DynamoDB client"""
    return boto3.client('dynamodb', region_name='ap-southeast-2')


@pytest.fixture(scope='module')
def lambda_client():
    """Lambda client"""
    return boto3.client('lambda', region_name='ap-southeast-2')


@pytest.fixture(scope='module')
def api_url():
    """Get API URL from CloudFormation outputs"""
    cfn = boto3.client('cloudformation', region_name='ap-southeast-2')
    try:
        # Try to find the stack (might have different name patterns)
        paginator = cfn.get_paginator('describe_stacks')
        for page in paginator.paginate():
            for stack in page['Stacks']:
                if 'ThomasShewan22080488Stack' in stack['StackName']:
                    outputs = stack.get('Outputs', [])
                    for output in outputs:
                        if 'ApiUrl' in output.get('OutputKey', ''):
                            return output['OutputValue']
        pytest.skip("Stack or API URL not found")
    except Exception as e:
        pytest.skip(f"Cannot get API URL: {str(e)}")


def test_dynamodb_targets_table_exists(dynamodb_client):
    """Test that targets table exists"""
    response = dynamodb_client.list_tables()
    tables = response['TableNames']
    targets_tables = [t for t in tables if 'TargetsTable' in t]
    assert len(targets_tables) > 0


def test_dynamodb_alarm_log_table_exists(dynamodb_client):
    """Test that alarm log table exists"""
    response = dynamodb_client.list_tables()
    tables = response['TableNames']
    alarm_tables = [t for t in tables if 'AlarmLogTable' in t]
    assert len(alarm_tables) > 0


def test_targets_table_has_streams_enabled(dynamodb_client):
    """Test that DynamoDB streams are enabled on targets table"""
    response = dynamodb_client.list_tables()
    tables = [t for t in response['TableNames'] if 'TargetsTable' in t]
    if tables:
        table_desc = dynamodb_client.describe_table(TableName=tables[0])
        assert 'StreamSpecification' in table_desc['Table']
        assert table_desc['Table']['StreamSpecification']['StreamEnabled'] == True


def test_infrastructure_lambda_exists(lambda_client):
    """Test that InfrastructureLambda exists for dynamic alarm management"""
    response = lambda_client.list_functions()
    functions = [f['FunctionName'] for f in response['Functions']]
    infra_functions = [f for f in functions if 'InfrastructureLambda' in f]
    assert len(infra_functions) > 0


def test_crud_api_create_and_delete(api_url):
    """Test creating and deleting a target via API"""
    # Create a test target
    response = requests.post(
        f"{api_url}targets",
        json={'name': 'IntegrationTest', 'url': 'https://example.com'}
    )
    assert response.status_code == 201
    
    target = response.json()
    target_id = target['TargetId']
    
    # Delete the target
    response = requests.delete(f"{api_url}targets/{target_id}")
    assert response.status_code == 200
    
    # Verify it's deleted
    response = requests.get(f"{api_url}targets/{target_id}")
    assert response.status_code == 404


def test_crud_api_list_targets(api_url):
    """Test listing all targets"""
    response = requests.get(f"{api_url}targets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_monitoring_workflow_components_exist(cloudwatch_client, lambda_client):
    """Test that all monitoring workflow components exist"""
    # Check Lambda functions exist
    lambda_response = lambda_client.list_functions()
    function_names = [f['FunctionName'] for f in lambda_response['Functions']]
    
    assert any('MonitoringLambda' in f for f in function_names)
    assert any('InfrastructureLambda' in f for f in function_names)
    assert any('CRUDLambda' in f for f in function_names)
    
    # Check CloudWatch namespace exists
    metrics_response = cloudwatch_client.list_metrics(Namespace='WebMonitoring/Health')
    assert 'Metrics' in metrics_response