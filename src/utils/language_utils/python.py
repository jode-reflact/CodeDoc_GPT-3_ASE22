import re

import tiktoken

from src.utils.language_utils.base import LanguageUtil

enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

class PythonUtils(LanguageUtil):
    def remove_comments(self, file_content:str)-> str:
        replacement_result = re.sub(pattern='"""[^"]*"""',
                                    flags=re.MULTILINE,
                                    repl='""""""',
                                    string=file_content)
        replacement_result = re.sub(pattern='^ *#.*\n?',
                                    flags=re.MULTILINE,
                                    repl='',
                                    string=replacement_result)
        return replacement_result
    
    def extract_functions_from_file(self, preprocessed_path: str) -> list[str]:
        functions: list = []
        inside_function: bool = False
        function_start_white_space_count: int = 0
        start_line: int = 0
        current_function:str = ''

        with open(preprocessed_path, 'r') as preprossedFile:
            for (line_index, line) in enumerate(preprossedFile, start=1):
                if not inside_function and self.is_start_of_function(line):
                    start_line = line_index
                    function_start_white_space_count = self.count_whitespace(line)
                    current_function = line
                    inside_function = True
                elif(inside_function):
                    current_whitespace_count = self.count_whitespace(line)
                    if (current_whitespace_count == function_start_white_space_count):
                        inside_function = False
                        
                        #functions shorter than three lines are not used
                        stop_words = []
                        if line_index - start_line >= 3:
                            if not any(stop_word in current_function for stop_word in stop_words):
                                if len(enc.encode(current_function)) < 2500:
                                    functions.append(current_function)
                        
                        if self.is_start_of_function(line):
                            start_line = line_index
                            function_start_white_space_count = self.count_whitespace(line)
                            current_function = line
                            inside_function = True
                    else:
                        current_function += line
        return functions
    
    def is_start_of_function(self, line: str)-> bool:
        line = re.sub("`.*`", "``", line)
        line = re.sub("'.*'", "''", line)
        line = re.sub("\".*\"", "\"\"", line)
        line = re.sub("^\s*", "", line)
        if line.startswith('def'):
            return True
        return False
    
    def count_whitespace(self, line: str)-> int:
        """Count trailing whitespace of line

        Args:
            line (str): Line of file

        Returns:
            int: Trailing whitespace count
        """
        return len(line) - len(line.lstrip())