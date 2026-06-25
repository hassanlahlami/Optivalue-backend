"""Routes fetch_history(history_code) to the right results client per league.

Different leagues draw history from different sources (club CSVs vs national-team data),
but the pipeline calls a single results client with just a history_code. This composite
looks up which league owns that code, reads its history_source, and delegates. Keeping
the BaseResultsClient interface unchanged means fit_models needs no special-casing.
"""
from __future__ import annotations
import logging
import pandas as pd
from .base import BaseResultsClient

log = logging.getLogger(__name__)


class CompositeResultsClient(BaseResultsClient):
    def __init__(self, clients_by_source: dict, leagues) -> None:
        # clients_by_source: {"footballdata_couk": client, "international": client, ...}
        self.clients_by_source = clients_by_source
        self.source_by_code = {lg.history_code: lg.history_source for lg in leagues}

    def fetch_history(self, history_code: str) -> pd.DataFrame:
        source = self.source_by_code.get(history_code, "footballdata_couk")
        client = self.clients_by_source.get(source)
        if client is None:
            log.error("no results client for source %r (history_code %s)", source, history_code)
            return pd.DataFrame()
        return client.fetch_history(history_code)
