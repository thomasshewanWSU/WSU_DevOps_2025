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

# Core Infrastructure Tests (5 tests)

def test_lambda_functions_created(template):
    """Four Lambda functions should be created: CRUD, Monitoring, DashboardManager, AlarmLogger"""
    template.resource_count_is("AWS::Lambda::Function", 4)


def test_cloudwatch_dashboards_created(template):
    """Two CloudWatch dashboards should exist: Lambda Operations + Website Health"""
    template.resource_count_is("AWS::CloudWatch::Dashboard", 2)


def test_dynamodb_tables_created(template):
    """Two DynamoDB tables should exist: Targets + AlarmLog"""
    template.resource_count_is("AWS::DynamoDB::Table", 2)


def test_sns_topic_created(template):
    """SNS topic for alarms should exist"""
    template.resource_count_is("AWS::SNS::Topic", 1)


def test_lambda_alarms_created(template):
    """Only Lambda operational alarms should be created statically (3 total)"""
    template.resource_count_is("AWS::CloudWatch::Alarm", 3)


def test_eventbridge_rule_created(template):
    """EventBridge rule for scheduling should exist"""
    template.has_resource_properties(
        "AWS::Events::Rule",
        {"ScheduleExpression": "rate(5 minutes)"},
    )


def test_api_gateway_created(template):
    """API Gateway should be created for CRUD operations"""
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_targets_table_has_streams(template):
    """Targets table should have DynamoDB streams enabled for DashboardManager"""
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "TableName": "WebMonitoringTargets",
            "StreamSpecification": {
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            }
        }
    )

# Dashboard Manager Tests (5 tests)

def test_dashboard_manager_lambda_properties(template):
    """Dashboard Manager Lambda should have correct properties"""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Runtime": "python3.11",
            "Handler": "DashboardManagerLambda.lambda_handler",
            "Timeout": 60,
        },
    )


def test_dashboard_manager_has_cloudwatch_permissions(template):
    """Dashboard Manager should have CloudWatch permissions"""
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Effect": "Allow",
                        "Action": assertions.Match.array_with([
                            "cloudwatch:PutDashboard",
                            "cloudwatch:PutMetricAlarm",
                            "cloudwatch:DeleteAlarms"
                        ])
                    })
                ])
            }
        }
    )


def test_dynamodb_stream_event_source(template):
    """DynamoDB stream should trigger Dashboard Manager Lambda"""
    template.has_resource_properties(
        "AWS::Lambda::EventSourceMapping",
        {
            "StartingPosition": "LATEST",
            "BatchSize": 1
        }
    )


def test_dashboard_manager_environment_variables(template):
    """Dashboard Manager should have required environment variables"""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "DashboardManagerLambda.lambda_handler",
            "Environment": {
                "Variables": {
                    "TARGETS_TABLE_NAME": {"Ref": assertions.Match.any_value()},
                    "DASHBOARD_NAME": "WebsiteHealthMonitoring",
                    "ALARM_TOPIC_ARN": {"Ref": assertions.Match.any_value()}
                }
            }
        }
    )


def test_crud_lambda_can_invoke_dashboard_manager(template):
    """CRUD Lambda should have permission to invoke Dashboard Manager"""
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Effect": "Allow",
                        "Action": "lambda:InvokeFunction"
                    })
                ])
            }
        }
    )