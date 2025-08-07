from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs
)
from constructs import Construct

class WebCrawlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda Role with CloudWatch permissions
        lambda_role = iam.Role(
            self, "WebCrawlerLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["cloudwatch:PutMetricData"],
            resources=["*"]
        ))

        # Lambda function
        web_crawler_lambda = _lambda.Function(
            self, "WebCrawlerLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="cloudWatchLambda.lambda_handler",
            code=_lambda.Code.from_asset("./modules"),
            timeout=Duration.seconds(60),
            memory_size=256,
            role=lambda_role,
            description="Web crawler monitoring multiple websites",
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Schedule every 5 minutes
        events.Rule(
            self, "WebCrawlerSchedule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
            targets=[targets.LambdaFunction(web_crawler_lambda)]
        )

        # Dashboard (3 metrics: Availability, Latency, Throughput)
        websites = ["Google", "GitHub", "AWS"]

        dashboard = cloudwatch.Dashboard(
            self, "WebCrawlerDashboard",
            dashboard_name="Website-Health-Monitor"
        )

            
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Availability",
                left=[
                    cloudwatch.Metric(
                        namespace="WebCrawler/Monitoring",
                        metric_name="Availability",
                        dimensions_map={"WebsiteName": site},
                        statistic="Average",
                        period=Duration.minutes(5),
                        label=site
                    ) for site in websites
                ]
            ),
            cloudwatch.GraphWidget(
                title="Latency (ms)",
                left=[
                    cloudwatch.Metric(
                        namespace="WebCrawler/Monitoring",
                        metric_name="Latency",
                        dimensions_map={"WebsiteName": site},
                        statistic="Average",
                        period=Duration.minutes(5),
                        label=site
                    ) for site in websites
                ]
            ),
            cloudwatch.GraphWidget(
                title="Throughput (Bytes/sec)",
                left=[
                    cloudwatch.Metric(
                        namespace="WebCrawler/Monitoring",
                        metric_name="Throughput",
                        dimensions_map={"WebsiteName": site},
                        statistic="Average",
                        period=Duration.minutes(5),
                        label=site
                    ) for site in websites
                ]
            ),
            cloudwatch.GraphWidget(
                title="Content Length (Bytes)",
                left=[
                    cloudwatch.Metric(
                        namespace="WebCrawler/Monitoring",
                        metric_name="ContentLength",
                        dimensions_map={"WebsiteName": site},
                        statistic="Average",
                        period=Duration.minutes(5),
                        label=site
                    ) for site in websites
                ]
            )
        )
            
