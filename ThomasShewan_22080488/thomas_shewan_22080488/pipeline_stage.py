from aws_cdk import Stage
from constructs import Construct
from .thomas_shewan_22080488_stack import ThomasShewan22080488Stack


class MyPipelineStage(Stage):
    """
    Deployment stage for the web monitoring application.
    
    Each stage represents a complete deployment environment with its own:
    - Lambda functions
    - DynamoDB tables
    - CloudWatch dashboards
    - API Gateway endpoints
    
    Stage names (construct_id) are used as prefixes to prevent resource name conflicts.
    For example, 'alpha' stage creates resources like 'alpha-WebMonitoring' Lambda.
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize a pipeline stage.
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Instantiate the application stack with stage-specific naming
        # The stage_name parameter ensures resource names are unique per environment
        # Stack documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/Stack.html
        ThomasShewan22080488Stack(
            self,
            "ThomasShewan22080488Stack",
            stage_name=construct_id  # Examples: 'alpha', 'prod'
        )