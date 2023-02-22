from launart import Service
from launart.component import Launchable
from launart.service import ExportInterface

from .database import DataBase


class DataBaseService(Launchable):
    id = "db.database"

    @property
    def required(self) -> set[str | type[ExportInterface]]:
        return set()

    @property
    def stages(self) -> set[str]:
        return {"preparing", "cleanup"}

    async def launch(self, _):
        async with self.stage("preparing"):
            await DataBase.create_all()
        async with self.stage("cleanup"):
            await DataBase.showdown()
