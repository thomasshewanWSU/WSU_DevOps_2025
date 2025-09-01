from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_dynamodb as dynamodb,
    aws_cloudwatch_actions as cloudwatch_actions,
)
from constructs import Construct

class ThomasShewan22080488Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Lambda function for canary monitoring
        canary_lambda = lambda_.Function(
            self, "MonitoringLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="MonitoringLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            timeout=Duration.seconds(60), 
            description="Web health monitoring canary - crawls multiple websites"
        )
        
        # CloudWatch permissions to Lambda
        canary_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:PutMetricData"
                ],
                resources=["*"]
            )
        )

        # SNS Topic for alarm notifications
        alarm_topic = sns.Topic(
            self, "AlarmNotificationTopic",
            display_name="Web Monitoring Alarm Notifications"
        )

        alarm_log_table = dynamodb.Table(
            self, "AlarmLogTable",
            partition_key=dynamodb.Attribute(
                name="AlarmName",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="Timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY  # For dev/demo only
        )
        alarm_logger_lambda = lambda_.Function(
            self, "AlarmLoggerLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="AlarmLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            environment={
                "ALARM_LOG_TABLE": alarm_log_table.table_name
            },
            timeout=Duration.seconds(30),
            description="Logs alarm notifications to DynamoDB"
        )
        alarm_log_table.grant_write_data(alarm_logger_lambda)
        alarm_topic.add_subscription(
            subscriptions.LambdaSubscription(alarm_logger_lambda)
        )
        # EventBridge rule to trigger Lambda every 5 minutes
        monitoring_rule = events.Rule(
            self, "MonitoringScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
            description="Trigger web monitoring every 5 minutes"
        )
        
        # Lambda as target for the EventBridge rule
        monitoring_rule.add_target(
            targets.LambdaFunction(canary_lambda)
        )
        
        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self, "WebHealthDashboard",
            dashboard_name="WebsiteHealthMonitoring"
        )
        
        websites = ["Google", "Amazon", "GitHub"]
        
        availability_metrics = []
        latency_metrics = []
        throughput_metrics = []
        
        for website in websites:
            metrics = self.create_website_monitoring(website, dashboard, alarm_topic)
            availability_metrics.append(metrics['availability'])
            latency_metrics.append(metrics['latency'])
            throughput_metrics.append(metrics['throughput'])
        
        # dashboard widgets
        dashboard.add_widgets(
            # Availability widget
            cloudwatch.GraphWidget(
                title="Website Availability (All Sites)",
                left=availability_metrics,
                width=12,
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0,
                    max=1.1
                )
            ),
            
            # Latency widget
            cloudwatch.GraphWidget(
                title="Response Time - All Websites (ms)",
                left=latency_metrics,
                width=12,
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0
                )
            ),
            
            # Throughput widget
            cloudwatch.GraphWidget(
                title="Throughput - All Websites (bytes/sec)",
                left=throughput_metrics,
                width=12,
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0
                )
            )
        )
        
        print(f"Created monitoring Lambda: {canary_lambda.function_name}")
        print("Lambda will be triggered every 5 minutes via EventBridge")
        print(f"CloudWatch Dashboard: {dashboard.dashboard_name}")
    
    # Defining Metrics for each website
    def create_website_monitoring(self, website_name: str, dashboard: cloudwatch.Dashboard, alarm_topic: sns.Topic):
        """Create monitoring setup for a single website"""
        
        availability_metric = cloudwatch.Metric(
            namespace="WebMonitoring/Health",
            metric_name="Availability",
            dimensions_map={"Website": website_name},
            statistic="Average",
            period=Duration.minutes(5)
        )
        
        latency_metric = cloudwatch.Metric(
            namespace="WebMonitoring/Health",
            metric_name="Latency",
            dimensions_map={"Website": website_name},
            statistic="Average",
            period=Duration.minutes(5)
        )
        
        throughput_metric = cloudwatch.Metric(
            namespace="WebMonitoring/Health",
            metric_name="Throughput",
            dimensions_map={"Website": website_name},
            statistic="Average",
            period=Duration.minutes(5)
        )
        
        # Availability Alarm (alert when site is down)
        availability_alarm = cloudwatch.Alarm(
            self, f"{website_name}AvailabilityAlarm",
            alarm_name=f"{website_name}-Availability-Alarm",
            alarm_description=f"Alert when {website_name} is unavailable",
            metric=availability_metric,
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            evaluation_periods=2,  
            datapoints_to_alarm=2,
            treat_missing_data=cloudwatch.TreatMissingData.BREACHING
        )
        availability_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Latency Alarm (alert when response time > 5000ms)
        latency_alarm = cloudwatch.Alarm(
            self, f"{website_name}LatencyAlarm",
            alarm_name=f"{website_name}-Latency-Alarm", 
            alarm_description=f"Alert when {website_name} response time exceeds 5000ms",
            metric=latency_metric,
            threshold=5000,  
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            evaluation_periods=3,  
            datapoints_to_alarm=2,  
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        latency_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Throughput Alarm (alert when throughput drops below threshold)
        throughput_alarm = cloudwatch.Alarm(
            self, f"{website_name}ThroughputAlarm",
            alarm_name=f"{website_name}-Throughput-Alarm",
            alarm_description=f"Alert when {website_name} throughput drops below 1000 bytes/sec",
            metric=throughput_metric,
            threshold=1000,  
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            evaluation_periods=3,  
            datapoints_to_alarm=2,  
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        throughput_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Return metrics for dashboard consolidation
        return {
            'availability': availability_metric,
            'latency': latency_metric, 
            'throughput': throughput_metric
        }