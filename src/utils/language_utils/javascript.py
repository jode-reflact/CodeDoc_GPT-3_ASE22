import re

import tiktoken

from src.utils.language_utils.base import LanguageUtil

enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

class JavascriptUtils(LanguageUtil):

    def remove_comments(self, file_content:str)-> str:
        replacement_result = re.sub(pattern="\/\*[\s\S]*?\*\/|([^\\:]|^)\/\/.*$",
            flags=re.MULTILINE,
            repl=r'\1',
            string=file_content)
        return replacement_result
    
    def extract_functions_from_file(self, preprocessed_path: str) -> list[str]:
        functions: list = []
        insideFunction: bool = False
        hasLineWithMoreOpenBrackets: bool = False
        startLine: int = 0
        openCount: int = 0
        closeCount: int = 0
        current_function:str = ''

        # string not in quotes --> function(?=([^[`\"']]*[`\"'][^[`\"']]*[`\"'])*[^[`\"']]*$)

        with open(preprocessed_path, 'r') as preprossedFile:
            for (line_index, line) in enumerate(preprossedFile, start=1):
                if not insideFunction and self.is_start_of_function(line):
                    openCount = 0
                    closeCount = 0
                    startLine = line_index
                    current_function = ''
                    # FOR DEBUGGING: 
                    #currentFunction = '// FUNCTION BEGIN\n'
                    hasLineWithMoreOpenBrackets = False
                    insideFunction = True
                openCount += line.count('{')
                closeCount += line.count('}')
                if(insideFunction):
                    if(not hasLineWithMoreOpenBrackets):
                        hasLineWithMoreOpenBrackets = self.is_line_with_more_open_brackets(openCount, closeCount)
                    current_function += line
                    if (hasLineWithMoreOpenBrackets and self.is_end_of_function(openCount, closeCount)):
                        insideFunction = False
                        
                        #functions shorter than three lines are not used
                        stop_words = ['webpack'] # "use strict"
                        if line_index - startLine >= 3:
                            if not any(stop_word in current_function for stop_word in stop_words):
                                if len(enc.encode(current_function)) < 2500:
                                    functions.append(current_function.strip())
                        # FOR DEBUGGING: currentFunction += '// FUNCTION END\n'
                        #documentedCode = documentCodeViaAI(currentFunction)
                        #documentedCode = currentFunction
        return functions

    def is_start_of_function(self, line: str)-> bool:
        line = re.sub("`.*`", "``", line)
        line = re.sub("'.*'", "''", line)
        line = re.sub("\".*\"", "\"\"", line)
        if 'function' in line:
            return True
        return False
    def is_end_of_function(self, open_count: int, close_count: int)-> bool:
        """Is line end of current function

        Args:
            open_count (int): Number of opening brackets "{"
            close_count (int): Number of closing brackets "}"

        Returns:
            bool: Whether is end of function
        """
        if (open_count == 0 or close_count == 0):
            return False
        return open_count == close_count
    def is_line_with_more_open_brackets(self, open_count: int, close_count: int)-> bool:
        """Whether a link has more open brackets than closed

        Args:
            open_count (int): Number of opening brackets "{"
            close_count (int): Number of closing brackets "}"

        Returns:
            bool: Whether open count is greater than close count
        """
        if (open_count == 0 and close_count == 0):
            return False
        return open_count > close_count