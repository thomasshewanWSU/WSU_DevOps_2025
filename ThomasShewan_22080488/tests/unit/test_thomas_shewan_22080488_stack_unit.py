import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack


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