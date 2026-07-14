from functools import lru_cache

from app.catalog_sync import CatalogSyncScheduler
from app.catalog import CatalogRepository
from app.config import Settings, get_settings
from app.course_matcher import CourseMatcher
from app.database import Database
from app.dialog_manager import DialogManager
from app.llm_client import OpenRouterClient
from app.llm_profile_extractor import LLMProfileExtractor
from app.llm_track_builder import LLMTrackBuilder
from app.track_builder import TrackBuilder


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.sqlite_path)
        self.catalog = CatalogRepository(settings.catalog_seed_path)
        self.catalog_sync_scheduler = CatalogSyncScheduler(settings)
        self.rule_based_track_builder = TrackBuilder()
        self.llm_client = OpenRouterClient(settings)
        self.profile_extractor = LLMProfileExtractor(self.llm_client)
        self.course_matcher = CourseMatcher(self.llm_client)
        self.track_builder = LLMTrackBuilder(self.llm_client, self.rule_based_track_builder)
        self.dialog_manager = DialogManager(
            self.database,
            self.catalog,
            self.track_builder,
            self.profile_extractor,
            self.course_matcher,
        )


@lru_cache
def get_container() -> Container:
    return Container(get_settings())
