"""Theory X — Stage 1: Sense Stream.

Factory function `build_scheduler(writers, readers)` wires all 23
adapters and returns a ready SenseScheduler. Call it after the substrate
is initialized; pass the live Writer/Reader maps from AppState.

Internal sensors start immediately. External feeds start paused.
"""
from __future__ import annotations

from substrate import Reader, Writer
from .scheduler import SenseScheduler

# Internal sensors
from .internal.proprioception import Proprioception
from .internal.temporal import Temporal
from .internal.interoception import Interoception
from .internal.meta_awareness import MetaAwareness

# External feeds (1-19)
from .feeds.arxiv_ai import ArxivAI
from .feeds.papers_with_code import PapersWithCode
from .feeds.lab_blogs import LabBlogs
from .feeds.ml_conferences import MLConferences
from .feeds.hacker_news import HackerNews
from .feeds.mit_tech_review import MITTechReview
from .feeds.ieee_spectrum import IEEESpectrum
from .feeds.arxiv_emerging import ArxivEmerging
from .feeds.biorxiv_neuro import BiorxivNeuro
from .feeds.frontiers_neuro import FrontiersNeuro
from .feeds.philpapers import PhilPapers
from .feeds.arxiv_computing import ArxivComputing
from .feeds.tech_news import TechNews
from .feeds.coingecko import CoinGecko
from .feeds.exchange_prices import ExchangePrices
from .feeds.crypto_news import CryptoNews
from .feeds.reuters import Reuters
from .feeds.ap_news import APNews
from .feeds.bbc_news import BBCNews

THEORY_X_STAGE = 1

__all__ = ["build_scheduler", "SenseScheduler"]


def build_scheduler(
    writers: dict[str, Writer],
    readers: dict[str, Reader],
) -> SenseScheduler:
    """Create, wire, and return a SenseScheduler with all 23 adapters.

    The sense.db Writer is the only write destination. The beliefs.db
    Reader is passed to interoception. MetaAwareness receives a
    late-bound state dict that is populated with the scheduler reference
    after construction — poll() only reads it lazily.

    External feeds start paused. Internal sensors start immediately.
    """
    sense_writer = writers["sense"]
    beliefs_reader = readers["beliefs"]

    # State container for meta_awareness — filled after scheduler is built.
    _meta_state: dict = {"scheduler": None, "writers": writers}

    adapters = [
        # Internal sensors (feeds 20-23) — always enabled
        Proprioception(sense_writer),
        Temporal(sense_writer),
        Interoception(sense_writer, beliefs_reader=beliefs_reader),
        MetaAwareness(sense_writer, meta_state=_meta_state),

        # External feeds (1-19) — start paused
        ArxivAI(sense_writer),
        PapersWithCode(sense_writer),
        LabBlogs(sense_writer),
        MLConferences(sense_writer),
        HackerNews(sense_writer),
        MITTechReview(sense_writer),
        IEEESpectrum(sense_writer),
        ArxivEmerging(sense_writer),
        BiorxivNeuro(sense_writer),
        FrontiersNeuro(sense_writer),
        PhilPapers(sense_writer),
        ArxivComputing(sense_writer),
        TechNews(sense_writer),
        CoinGecko(sense_writer),
        ExchangePrices(sense_writer),
        CryptoNews(sense_writer),
        Reuters(sense_writer),
        APNews(sense_writer),
        BBCNews(sense_writer),
    ]

    scheduler = SenseScheduler(adapters)
    _meta_state["scheduler"] = scheduler   # late-bind for meta_awareness

    return scheduler
