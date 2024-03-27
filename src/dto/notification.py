from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Notification(ABC):
    @classmethod
    @abstractmethod
    def from_notification(cls, notification_text: str):
        pass

    @abstractmethod
    def prep_vkt_message(self):
        pass
