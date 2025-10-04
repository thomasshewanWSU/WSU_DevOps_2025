import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack
from unittest.mock import patch
from modules import CrudLambda
import json

@pytest.fixture
def stack():
    app = cdk.App()
    return ThomasShewan22080488Stack(app, "thomas-shewan-22080488")


@pytest.fixture
def template(stack):
    return assertions.Template.from_stack(stack)


def test_lambda_functions_created(template):
    """Both Lambda functions should be created"""
    template.resource_count_is("AWS::Lambda::Function", 2)


def test_monitoring_lambda_properties(template):
    """Monitoring Lambda should have correct properties"""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Runtime": "python3.11",
            "Handler": "MonitoringLambda.lambda_handler",
            "Timeout": 60,
        },
    )


def test_eventbridge_rule_created(template):
    """EventBridge rule for scheduling should exist"""
    template.has_resource_properties(
        "AWS::Events::Rule",
        {"ScheduleExpression": "rate(5 minutes)"},
    )


def test_cloudwatch_dashboard_created(template):
    """CloudWatch dashboard should exist"""
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)


def test_sns_topic_created(template):
    """SNS topic for alarms should exist"""
    template.resource_count_is("AWS::SNS::Topic", 1)


def test_dynamodb_table_created(template):
    """DynamoDB table for alarm logging should exist"""
    template.resource_count_is("AWS::DynamoDB::Table", 1)


def test_cloudwatch_alarms_created(template):
    """All alarms should be created (12 in total: 9 website + 3 Lambda)"""
    template.resource_count_is("AWS::CloudWatch::Alarm", 12)

# CRUD Tests

def test_create_target_success():
    """Test successful target creation"""
    event = {
        'httpMethod': 'POST',
        'path': '/targets',
        'body': json.dumps({
            'name': 'TestSite',
            'url': 'https://example.com'
        })
    }
    
    with patch('CrudLambda.table') as mock_table:
        mock_table.put_item.return_value = {}
        response = CrudLambda.lambda_handler(event, {})
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['name'] == 'TestSite'
        assert 'TargetId' in body

def test_list_targets():
    """Test listing all targets"""
    event = {
        'httpMethod': 'GET',
        'path': '/targets'
    }
    
    with patch('CrudLambda.table') as mock_table:
        mock_table.scan.return_value = {
            'Items': [{'TargetId': '123', 'name': 'Test', 'url': 'https://test.com'}]
        }
        response = CrudLambda.lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 1

def test_update_target():
    """Test updating a target"""
    event = {
        'httpMethod': 'PUT',
        'path': '/targets/123',
        'pathParameters': {'id': '123'},
        'body': json.dumps({'name': 'Updated'})
    }
    
    with patch('CrudLambda.table') as mock_table:
        mock_table.get_item.return_value = {'Item': {'TargetId': '123'}}
        mock_table.update_item.return_value = {
            'Attributes': {'TargetId': '123', 'name': 'Updated'}
        }
        response = CrudLambda.lambda_handler(event, {})
        
        assert response['statusCode'] == 200

def test_delete_target():
    """Test deleting a target"""
    event = {
        'httpMethod': 'DELETE',
        'path': '/targets/123',
        'pathParameters': {'id': '123'}
    }
    
    with patch('CrudLambda.table') as mock_table:
        mock_table.get_item.return_value = {'Item': {'TargetId': '123'}}
        mock_table.delete_item.return_value = {}
        response = CrudLambda.lambda_handler(event, {})
        
        assert response['statusCode'] == 200