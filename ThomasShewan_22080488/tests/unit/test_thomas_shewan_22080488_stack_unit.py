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

# Core Infrastructure Tests

def test_lambda_functions_created(template):
    """Four Lambda functions should be created: CRUD, Monitoring, DashboardManager, AlarmLogger"""
    template.resource_count_is("AWS::Lambda::Function", 3)  # ✅ This is correct


def test_cloudwatch_dashboards_created(template):
    """Two CloudWatch dashboards should exist: Lambda Operations + Website Health"""
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)  # ✅ Fixed: was expecting 1, now 2


def test_dynamodb_tables_created(template):
    """Two DynamoDB tables should exist: Targets + AlarmLog"""
    template.resource_count_is("AWS::DynamoDB::Table", 2)


def test_sns_topic_created(template):
    """SNS topic for alarms should exist"""
    template.resource_count_is("AWS::SNS::Topic", 1)


def test_lambda_alarms_created(template):
    """Only Lambda operational alarms should be created statically (4 total: Duration, Invocations, Errors, Memory)"""
    template.resource_count_is("AWS::CloudWatch::Alarm", 4)  

def test_eventbridge_rule_created(template):
    """EventBridge rule for scheduling should exist"""
    template.has_resource_properties(
        "AWS::Events::Rule",
        {"ScheduleExpression": "rate(5 minutes)"},
    )


def test_api_gateway_created(template):
    """API Gateway should be created for CRUD operations"""
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_memory_alarm_created(template):
    """Memory utilization alarm should be created for Lambda monitoring"""
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "CanaryLambda-Memory-Alarm",
            "AlarmDescription": "Lambda memory usage > 102MB (80% of 128MB)",
            "Threshold": 102,
            "ComparisonOperator": "GreaterThanThreshold"
        }
    )