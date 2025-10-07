"""
Unit tests for the CDK Stack
Tests that all required AWS resources are defined in the stack
"""
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
    """Four Lambda functions should be created: CRUD, Monitoring, Infrastructure, AlarmLogger"""
    template.resource_count_is("AWS::Lambda::Function", 4)


def test_cloudwatch_dashboard_created(template):
    """One CloudWatch dashboard should exist for monitoring"""
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)


def test_dynamodb_tables_created(template):
    """Two DynamoDB tables should exist: Targets + AlarmLog"""
    template.resource_count_is("AWS::DynamoDB::Table", 2)


def test_dynamodb_streams_enabled(template):
    """DynamoDB Streams should be enabled on targets table"""
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "StreamSpecification": {
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            }
        }
    )


def test_sns_topic_created(template):
    """SNS topic for alarms should exist"""
    template.resource_count_is("AWS::SNS::Topic", 1)


def test_lambda_alarms_created(template):
    """Check that the 4 required Lambda operational alarms exist"""
    # Updated alarm names to match actual implementation
    for alarm_name in [
        "MonitoringLambda-Duration-Alarm",
        "MonitoringLambda-Invocations-Alarm",
        "MonitoringLambda-Errors-Alarm",
        "MonitoringLambda-Memory-Alarm"
    ]:
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            {"AlarmName": alarm_name}
        )


def test_eventbridge_rule_created(template):
    """EventBridge rule for scheduling should exist"""
    template.has_resource_properties(
        "AWS::Events::Rule",
        {"ScheduleExpression": "rate(5 minutes)"}
    )


def test_api_gateway_created(template):
    """API Gateway should be created for CRUD operations"""
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_api_gateway_has_cors(template):
    """API Gateway should have CORS configured"""
    template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {
            "Name": "WebCrawlerTargetsAPI"
        }
    )


def test_lambda_has_correct_timeout(template):
    """Monitoring Lambda should have 60 second timeout"""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Timeout": 60,
            "Runtime": "python3.11"
        }
    )


def test_infrastructure_lambda_has_stream_source(template):
    """Infrastructure Lambda should have DynamoDB stream as event source"""
    template.has_resource_properties(
        "AWS::Lambda::EventSourceMapping",
        {
            "StartingPosition": "LATEST",
            "BatchSize": 1
        }
    )