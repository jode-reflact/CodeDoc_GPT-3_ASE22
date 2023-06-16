import re

import tiktoken

from src.utils.language_utils.base import LanguageUtil

enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

class JavaUtils(LanguageUtil):
    def remove_comments(self, file_content:str)-> str:
        return ""
    
    def extract_functions_from_file(self, preprocessed_path: str) -> list[str]:
        return []