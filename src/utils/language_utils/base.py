from abc import ABC, abstractmethod


class LanguageUtil(ABC):
    @abstractmethod
    def remove_comments(self, file_content:str)-> str:
        pass

    @abstractmethod
    def extract_functions_from_file(self, preprocessed_path: str)-> list[str]:
        pass
