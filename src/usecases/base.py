from abc import ABC, abstractmethod


class ProjectServiceBase(ABC):
    @abstractmethod
    def who_i_am(self):
        pass
