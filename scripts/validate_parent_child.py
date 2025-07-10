#!/usr/bin/env python3
"""
Script de vérification des relations parent-enfant OpenTelemetry
"""

import asyncio
import uuid
import logging
from typing import Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TraceValidator:
    """Classe pour valider les relations parent-enfant"""

    def __init__(self):
        self.traces = {}

    def add_span(self, span_info: Dict[str, Any]):
        """Ajoute un span pour l'analyse"""
        trace_id = span_info.get('trace_id')
        if trace_id not in self.traces:
            self.traces[trace_id] = []
        self.traces[trace_id].append(span_info)

    def validate_relationships(self):
        """Valide les relations parent-enfant"""
        logger.info("🔍 Validation des relations parent-enfant")
        logger.info("=" * 50)

        for trace_id, spans in self.traces.items():
            logger.info(f"\n📊 Trace ID: {trace_id}")

            # Créer un mapping des spans
            span_map = {span['span_id']: span for span in spans}

            # Analyser chaque span
            for span in spans:
                parent_id = span.get('parent_id')
                correlation_id = span.get('correlation_id')

                if parent_id is None:
                    logger.info(
                        f"  🌳 ROOT: {span['name']} (correlation_id: {correlation_id})")
                else:
                    parent_span = span_map.get(parent_id)
                    if parent_span:
                        logger.info(
                            f"  📄 CHILD: {span['name']} -> PARENT: {parent_span['name']} (correlation_id: {correlation_id})")
                    else:
                        logger.warning(
                            f"  ⚠️  ORPHAN: {span['name']} - parent {parent_id} not found")

            # Vérifier la cohérence des correlation_id
            correlation_ids = {span.get('correlation_id')
                               for span in spans if span.get('correlation_id')}
            if len(correlation_ids) == 1:
                logger.info(
                    f"  ✅ Correlation ID cohérent: {list(correlation_ids)[0]}")
            elif len(correlation_ids) > 1:
                logger.warning(
                    f"  ⚠️  Multiple correlation IDs: {correlation_ids}")
            else:
                logger.warning(f"  ⚠️  Aucun correlation ID trouvé")


def simulate_trace_propagation():
    """Simule la propagation de trace entre services"""
    logger.info("🚀 Simulation de la propagation de trace")

    # Générer un correlation_id
    correlation_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    validator = TraceValidator()

    # Simuler le span root (setlist-agent)
    root_span = {
        'name': 'enhanced-agent-chat',
        'trace_id': trace_id,
        'span_id': 'span_001',
        'parent_id': None,
        'correlation_id': correlation_id,
        'service': 'setlist-agent'
    }
    validator.add_span(root_span)

    # Simuler le span enfant (spotify-mcp-server)
    spotify_span = {
        'name': 'spotify_mcp_search_tracks',
        'trace_id': trace_id,
        'span_id': 'span_002',
        'parent_id': 'span_001',  # Parent = root span
        'correlation_id': correlation_id,
        'service': 'spotify-mcp-server'
    }
    validator.add_span(spotify_span)

    # Simuler le span petit-enfant (API Spotify)
    spotify_api_span = {
        'name': 'spotify_api_request',
        'trace_id': trace_id,
        'span_id': 'span_003',
        'parent_id': 'span_002',  # Parent = spotify span
        'correlation_id': correlation_id,
        'service': 'spotify-mcp-server'
    }
    validator.add_span(spotify_api_span)

    # Simuler le span enfant (setlistfm-mcp-server)
    setlistfm_span = {
        'name': 'setlistfm_mcp_search_artist',
        'trace_id': trace_id,
        'span_id': 'span_004',
        'parent_id': 'span_001',  # Parent = root span
        'correlation_id': correlation_id,
        'service': 'setlistfm-mcp-server'
    }
    validator.add_span(setlistfm_span)

    # Simuler le span petit-enfant (API SetlistFM)
    setlistfm_api_span = {
        'name': 'setlistfm_api_request',
        'trace_id': trace_id,
        'span_id': 'span_005',
        'parent_id': 'span_004',  # Parent = setlistfm span
        'correlation_id': correlation_id,
        'service': 'setlistfm-mcp-server'
    }
    validator.add_span(setlistfm_api_span)

    # Valider les relations
    validator.validate_relationships()

    return validator


def test_broken_relationships():
    """Teste le cas où les relations parent-enfant sont brisées"""
    logger.info("\n🔴 Test des relations brisées")
    logger.info("=" * 30)

    validator = TraceValidator()

    # Span orphelin (parent_id introuvable)
    orphan_span = {
        'name': 'orphan_span',
        'trace_id': 'trace_123',
        'span_id': 'span_999',
        'parent_id': 'span_nonexistent',  # Parent inexistant
        'correlation_id': 'corr_123',
        'service': 'test-service'
    }
    validator.add_span(orphan_span)

    # Spans avec correlation_id différents
    span1 = {
        'name': 'span_with_corr1',
        'trace_id': 'trace_123',
        'span_id': 'span_100',
        'parent_id': None,
        'correlation_id': 'corr_different1',
        'service': 'test-service'
    }
    validator.add_span(span1)

    span2 = {
        'name': 'span_with_corr2',
        'trace_id': 'trace_123',
        'span_id': 'span_101',
        'parent_id': 'span_100',
        'correlation_id': 'corr_different2',  # Différent correlation_id
        'service': 'test-service'
    }
    validator.add_span(span2)

    # Valider les relations (devrait détecter les problèmes)
    validator.validate_relationships()


def main():
    """Fonction principale"""
    logger.info("🧪 Test des relations parent-enfant OpenTelemetry")
    logger.info("=" * 60)

    # Test normal
    simulate_trace_propagation()

    # Test des cas d'erreur
    test_broken_relationships()

    # Recommandations
    logger.info("\n📋 Recommandations pour une trace correcte:")
    logger.info("  ✅ Utiliser le même trace_id pour tous les spans")
    logger.info("  ✅ Définir parent_id correctement pour les spans enfants")
    logger.info("  ✅ Maintenir le même correlation_id dans toute la trace")
    logger.info("  ✅ Extraire et injecter le contexte de trace correctement")
    logger.info("  ✅ Valider les relations dans Azure Application Insights")

    logger.info("\n🎯 Requêtes Kusto utiles:")
    logger.info("  traces | where operation_Id == 'your-trace-id'")
    logger.info("  dependencies | where operation_Id == 'your-trace-id'")
    logger.info(
        "  traces | where customDimensions.correlation_id == 'your-correlation-id'")

    logger.info("\n🎉 Test terminé!")


if __name__ == "__main__":
    main()
