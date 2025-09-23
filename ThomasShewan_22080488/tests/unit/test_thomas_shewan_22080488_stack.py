import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack

@pytest.fixture
def stack():
    app = core.App()
    stack = ThomasShewan22080488Stack(app, "thomas-shewan-22080488")
    return stack

@pytest.fixture
def template(stack):
    return assertions.Template.from_stack(stack)

def test_lambda_functions_created(template):
    """Test that both Lambda functions are created"""
    template.resource_count_is("AWS::Lambda::Function", 2)

def test_monitoring_lambda_properties(template):
    """Test monitoring Lambda has correct properties"""
    template.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.11",
        "Handler": "MonitoringLambda.lambda_handler",
        "Timeout": 60
    })

def test_eventbridge_rule_created(template):
    """Test EventBridge rule for scheduling"""
    template.has_resource_properties("AWS::Events::Rule", {
        "ScheduleExpression": "rate(5 minutes)"
    })

def test_cloudwatch_dashboard_created(template):
    """Test CloudWatch dashboard exists"""
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)

def test_sns_topic_created(template):
    """Test SNS topic for alarms"""
    template.resource_count_is("AWS::SNS::Topic", 1)

def test_dynamodb_table_created(template):
    """Test DynamoDB table for alarm logging"""
    template.resource_count_is("AWS::DynamoDB::Table", 1)

def test_cloudwatch_alarms_created(template):
    """Test that alarms are created for each website"""
    template.resource_count_is("AWS::CloudWatch::Alarm", 9)