import resource
from botocore.endpoint import Endpoint
import logging
import os

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource

def setup_logging() -> LoggerProvider:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")

    # Add resource metadata that allows log aggregation by service name
    resource = Resource({"service.name":"basic_chatbot"})

    # Set up the provider which holds the pipeline config
    provider = LoggerProvider(resource=resource)

    # Set up the exporter which forwards logs to their destination
    exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs")

    # Get a Batch processor which buffers incoming logs and flushes them to the exporter
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter=exporter))

    # Bring in the standard lib handler which will emit into the OTEL provider
    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)

    # Attach to the root logger so all stdlib logs will flow to the exporter
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(logging.StreamHandler()) # Ensures we also log to the console

    return provider
