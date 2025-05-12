# ruff: noqa: ANN201, ANN001

import logging
import os
import sys

from dotenv import load_dotenv

from azure.ai.inference.tracing import AIInferenceInstrumentor
from azure.ai.projects import AIProjectClient
from azure.core.settings import settings
from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor

settings.tracing_implementation = "opentelemetry"

# https://learn.microsoft.com/en-sg/answers/questions/2243029/not-able-to-configure-the-tracing-for-azure-ai-fou


# load environment variables from the .env file

load_dotenv()

# Configure an root app logger that prints info level logs to stdout
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
print(f"Logger name: {logger.name}")
handler.setFormatter(formatter)
logger.addHandler(handler)
# logger.addHandler(logging.StreamHandler(stream=sys.stdout))
# logging.getLogger('azure.monitor.opentelemetry.exporter').setLevel(
#    logging.WARNING)
# logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(
#    logging.WARNING)
# Returns a module-specific logger, inheriting from the root app logger


# Enable instrumentation and logging of telemetry to the project
def enable_telemetry(log_to_project: bool = False):
    os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
    os.environ["ENABLE_AZURE_AI_PROJECTS_CONSOLE_LOGGING"] = "true"
    logger.info("Enabling telemetry logging...")
    AIInferenceInstrumentor().instrument()

    logger.info("Enabling OpenAI instrumentation...")
    OpenAIInstrumentor().instrument()

    # enable logging message contents
    if log_to_project:
        try:
            endpoint = os.environ["PROJECT_ENDPOINT"]
        except KeyError:
            logger.error("PROJECT_ENDPOINT environment variable is not set.")
            return
        logger.info("Project Endpoint: %s", endpoint)
        try:
            with DefaultAzureCredential() as credential:
                logger.info(
                    f"Using DefaultAzureCredential for authentication: {credential.__class__.__name__}")
                try:
                    with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
                        logger.info(
                            "Get the Application Insights connection string:")
                        connection_string = project_client.telemetry.get_connection_string()
                        os.environ["APPLICATION_INSIGHTS_CONNECTION_STRING"] = connection_string
                        logger.info(f"Connection String: {connection_string}")
                        if not connection_string:
                            logger.error(
                                "Application Insights is not enabled. Enable by going to Tracing in your Azure AI Foundry project.")
                        else:
                            logger.info(
                                "Configuring Azure Monitor with connection string")
                            configure_azure_monitor(
                                connection_string=connection_string, credential=credential, instrumentation_options={
                                    "azure_sdk": {"enabled": True},
                                    "django": {"enabled": True},
                                    "fastapi": {"enabled": False},
                                    "flask": {"enabled": True},
                                    "psycopg2": {"enabled": False},
                                    "requests": {"enabled": True},
                                    "urllib": {"enabled": True},
                                    "urllib3": {"enabled": True},
                                })
                except Exception as e:
                    logger.error(
                        f"Failed to get Application Insights connection string or configure Azure Monitor: {e}")
        except Exception as e:
            logger.error(
                f"Failed to authenticate with DefaultAzureCredential: {e}")
