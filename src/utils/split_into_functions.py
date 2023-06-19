import argparse
import os
import re
import sys
import time
from typing import List, TypedDict

import pandas as pd
import tiktoken

from src.utils.argparser import Arguments
from src.utils.language_utils.base import LanguageUtil
from src.utils.language_utils.java import JavaUtils
from src.utils.language_utils.javascript import JavascriptUtils
from src.utils.language_utils.python import PythonUtils


class Function(TypedDict):
    repo: str
    path: str
    code: str

enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

class FunctionSplitter():
    language_util: LanguageUtil

    def __init__(self, args: Arguments, repo_name: str, repo_path: str, files: list[str]):
        if args.language == "javascript":
            self.language_util = JavascriptUtils()
        elif args.language == "python":
            self.language_util = PythonUtils()
        elif args.language == "java":
            self.language_util = JavaUtils()
        else:
            raise NotImplementedError("Language not implemented")

        samples_path = os.sep.join(['data','raw', 'repo-samples_' + args.language + '.xlsx'])
        
        if os.path.exists(samples_path):
            samples_df = pd.read_excel(samples_path)
        else:
            samples_df = pd.DataFrame(columns=['repo', 'path', 'code'])

        for file in files:
            file_path = os.sep.join([repo_path, file])
            file_name = os.path.basename(file)

            if not os.path.exists(file_path):
                print(f"FILE_PATH {file_path} does not exist, aborting")
                sys.exit(os.EX_USAGE)

            preprocessed_folder = os.sep.join(['preprocessed', repo_name])
            preprocessed_path = os.sep.join([preprocessed_folder, file_name])

            if not os.path.exists(preprocessed_folder):
                os.makedirs(preprocessed_folder)

            if self.is_file_already_finished(samples_df, file, repo_name):
                print(f"FILE {file_path} already finished")
                continue
            
            if not os.path.isfile(file_path):
                continue

            if not os.path.exists(preprocessed_path):
                self.preprocess_file(file_path, preprocessed_path)

            function_codes: List[str] = self.language_util.extract_functions_from_file(preprocessed_path)
            functions: List[Function] = map(lambda code: {"repo": repo_name, "path": file, "code": code}, function_codes)
            df_extended = pd.DataFrame(functions, columns=['repo', 'path', 'code'])
            samples_df = pd.concat([samples_df, df_extended], ignore_index=True)
            samples_df.to_excel(samples_path, index=False)                

    def preprocess_file(self, file_path: str, preprocessed_path:str):
        with open(file_path, "r") as file:
            file_content = file.read()
            replacement_result = self.language_util.remove_comments(file_content)
            with open(preprocessed_path, "w") as preprossedFile:
                preprossedFile.write(replacement_result)

    def is_file_already_finished(self,samples_df: pd.DataFrame, path: str, repo_name: str)-> bool:
        """checks if file path is already included in xlsx dataframe -> file is already finished then

        Args:
            samples_df (pd.DataFrame): XLSX Dataframe
            path (str): file path

        Returns:
            bool: wheter it is already included
        """
        return ((samples_df['path'] == path) & (samples_df['repo'] == repo_name)).any()