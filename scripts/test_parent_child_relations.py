#!/usr/bin/env python3
"""
Script pour tester les relations parent-enfant dans le tracing OpenTelemetry
"""

import asyncio
import uuid
import logging
from opentelemetry import trace, context, baggage
from opentelemetry.propagate import get_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configuration des propagateurs
propagator = CompositeHTTPPropagator([
    TraceContextTextMapPropagator(),
    W3CBaggagePropagator(),
])
set_global_textmap(propagator)

# Exporteur pour la console
console_exporter = ConsoleSpanExporter()
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(console_exporter)
)


class SpanAnalyzer:
    """Classe pour analyser les relations parent-enfant des spans"""

    def __init__(self):
        self.spans = []
        self.span_processor = SimpleSpanProcessor(self)

    def export(self, spans):
        """Collect spans for analysis"""
        self.spans.extend(spans)
        return console_exporter.export(spans)

    def analyze_parent_child_relationships(self):
        """Analyse les relations parent-enfant"""
        logger.info("=== ANALYSE DES RELATIONS PARENT-ENFANT ===")

        # Grouper par trace_id
        traces = {}
        for span in self.spans:
            trace_id = span.get_span_context().trace_id
            if trace_id not in traces:
                traces[trace_id] = []
            traces[trace_id].append(span)

        for trace_id, spans in traces.items():
            logger.info(f"\nTrace ID: {trace_id}")

            # Construire l'arbre parent-enfant
            span_dict = {span.get_span_context(
            ).span_id: span for span in spans}
            root_spans = []

            for span in spans:
                parent_id = span.parent.span_id if span.parent else None
                if parent_id is None:
                    root_spans.append(span)
                    logger.info(
                        f"  🌳 ROOT: {span.name} (span_id: {span.get_span_context().span_id})")
                else:
                    parent_span = span_dict.get(parent_id)
                    if parent_span:
                        logger.info(
                            f"  📄 CHILD: {span.name} (span_id: {span.get_span_context().span_id}) -> PARENT: {parent_span.name}")
                    else:
                        logger.info(
                            f"  ⚠️  ORPHAN: {span.name} (span_id: {span.get_span_context().span_id}) - parent not found")

            # Vérifier les correlation_ids
            correlation_ids = set()
            for span in spans:
                attrs = span.attributes or {}
                corr_id = attrs.get('correlation_id')
                if corr_id:
                    correlation_ids.add(corr_id)

            logger.info(f"  📊 Correlation IDs trouvés: {correlation_ids}")

            if len(correlation_ids) > 1:
                logger.warning(
                    f"  ⚠️  Multiple correlation IDs dans le même trace: {correlation_ids}")
            elif len(correlation_ids) == 1:
                logger.info(
                    f"  ✅ Correlation ID cohérent: {list(correlation_ids)[0]}")


async def simulate_setlist_agent_call():
    """Simulation d'un appel depuis setlist-agent"""
    correlation_id = str(uuid.uuid4())
    logger.info(
        f"🎯 Simulation d'un appel setlist-agent avec correlation_id: {correlation_id}")

    # Span racine (setlist-agent)
    with tracer.start_as_current_span("enhanced-agent-chat") as root_span:
        root_span.set_attribute("service.name", "setlist-agent")
        root_span.set_attribute("correlation_id", correlation_id)

        # Définir le baggage avec correlation_id
        baggage_context = baggage.set_baggage("correlation_id", correlation_id)

        # Créer des headers avec le contexte de trace
        headers = {}
        propagator.inject(headers, context=baggage_context)

        logger.info(f"📤 Headers générés: {headers}")

        # Simuler l'appel au serveur MCP Spotify
        await simulate_spotify_mcp_call(headers)

        # Simuler l'appel au serveur MCP SetlistFM
        await simulate_setlistfm_mcp_call(headers)


async def simulate_spotify_mcp_call(headers: dict):
    """Simulation d'un appel au serveur MCP Spotify"""
    logger.info("🎵 Simulation d'un appel au serveur MCP Spotify")

    # Extraire le contexte des headers (ce que fait le serveur MCP)
    extracted_context = propagator.extract(headers)
    correlation_id = baggage.get_baggage(
        "correlation_id", context=extracted_context)

    logger.info(f"📥 Contexte extrait - correlation_id: {correlation_id}")

    # Créer un span enfant avec le contexte extrait
    with tracer.start_as_current_span("spotify_mcp_search_tracks", context=extracted_context) as span:
        span.set_attribute("service.name", "spotify-mcp-server")
        span.set_attribute("operation.name", "search_tracks")
        if correlation_id:
            span.set_attribute("correlation_id", str(correlation_id))

        # Simuler un appel API interne
        await simulate_spotify_api_call()


async def simulate_setlistfm_mcp_call(headers: dict):
    """Simulation d'un appel au serveur MCP SetlistFM"""
    logger.info("🎪 Simulation d'un appel au serveur MCP SetlistFM")

    # Extraire le contexte des headers
    extracted_context = propagator.extract(headers)
    correlation_id = baggage.get_baggage(
        "correlation_id", context=extracted_context)

    logger.info(f"📥 Contexte extrait - correlation_id: {correlation_id}")

    # Créer un span enfant avec le contexte extrait
    with tracer.start_as_current_span("setlistfm_mcp_search_artist", context=extracted_context) as span:
        span.set_attribute("service.name", "setlistfm-mcp-server")
        span.set_attribute("operation.name", "search_artist")
        if correlation_id:
            span.set_attribute("correlation_id", str(correlation_id))

        # Simuler un appel API interne
        await simulate_setlistfm_api_call()


async def simulate_spotify_api_call():
    """Simulation d'un appel API Spotify interne"""
    with tracer.start_as_current_span("spotify_api_request") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.url", "https://api.spotify.com/v1/search")
        await asyncio.sleep(0.1)  # Simuler une latence


async def simulate_setlistfm_api_call():
    """Simulation d'un appel API SetlistFM interne"""
    with tracer.start_as_current_span("setlistfm_api_request") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute(
            "http.url", "https://api.setlist.fm/rest/1.0/search/artists")
        await asyncio.sleep(0.1)  # Simuler une latence


async def main():
    """Fonction principale de test"""
    logger.info("🚀 Test des relations parent-enfant OpenTelemetry")
    logger.info("=" * 60)

    # Créer un analyseur de spans
    analyzer = SpanAnalyzer()
    trace.get_tracer_provider().add_span_processor(analyzer.span_processor)

    # Exécuter le test
    await simulate_setlist_agent_call()

    # Attendre un peu pour que tous les spans soient traités
    await asyncio.sleep(0.5)

    # Analyser les résultats
    analyzer.analyze_parent_child_relationships()

    logger.info("\n🎉 Test terminé!")


if __name__ == "__main__":
    asyncio.run(main())
