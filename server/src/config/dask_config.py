from pydantic_settings import BaseSettings
from functools import lru_cache


class DaskSettings(BaseSettings):
    scheduler_host: str = "localhost"
    scheduler_port: int = 8786
    dashboard_port: int = 8787
    n_workers: int = 2

    @property
    def scheduler_address(self) -> str:
        return f"tcp://{self.scheduler_host}:{self.scheduler_port}"

    class Config:
        env_prefix = "DASK_"


@lru_cache()
def get_dask_settings() -> DaskSettings:
    return DaskSettings()
