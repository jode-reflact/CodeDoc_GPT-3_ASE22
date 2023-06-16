import glob
import os
import shutil
import subprocess

import git
import pandas as pd
from dotenv import load_dotenv
from git import RemoteProgress
from github import Github, Repository

from src.utils.argparser import Argparser, Arguments
from src.utils.split_into_functions import FunctionSplitter

load_dotenv()
REPO_PATH = os.sep.join(['repos'])

if not os.path.exists(REPO_PATH):
   os.makedirs(REPO_PATH)

class CloneProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            print(message)

def cloneRepo(repo_link: str, clone_path: str):
    """Clone given Repository to disk

    Args:
        repoLink (str)
        clonePath (str)
    """
    git.Repo.clone_from(repo_link, clone_path, progress=CloneProgress())

def findAllFiles(args: Arguments, repo_path: str, dir_path: str = None):
    if dir_path is None:
        root_dir = repo_path
    else:
        root_dir = os.sep.join([repo_path, dir_path])
    file_suffix: str = ""
    if args.language == 'java':
        file_suffix = '.java'
    elif args.language == 'javascript':
        file_suffix = '.js'
    elif args.language == 'python':
        file_suffix = '.py'
    code_files = glob.glob("**/*"+file_suffix, root_dir=root_dir, recursive=True)
    if dir_path is not None:
        code_files = map(lambda code_file: os.sep.join([dir_path, code_file]), code_files)
    return code_files

def is_repo_finished(args: Arguments, repo_path: str):
    if not os.path.isfile(f'finished_repos_{args.language}.txt'):
        return False
    with open(f'finished_repos_{args.language}.txt', 'r') as file:
        content = file.read()
        return repo_path in content

def set_repo_finished(args: Arguments, repo_path: str):
    with open(f'finished_repos_{args.language}.txt', 'a') as file:
        file.write(repo_path + '\n')

def delete_repo_files(repo_path:str, repo_name: str):
    try:
        preprocessed_path = os.sep.join(['preprocessed', repo_name])
        shutil.rmtree(repo_path)
        #shutil.rmtree(preprocessed_path)
    except OSError as e:
        print("Error on deleting repo", e)
        quit()

def number_of_functions_in_xlsx(args: Arguments):
    samples_path = os.sep.join(['data','raw', 'repo-samples_' + args.language + '.xlsx'])
        
    if os.path.exists(samples_path):
        samples_df = pd.read_excel(samples_path)
        return len(samples_df)
    else:
        return 0

def main():
    # using an github access token from your environment, can be replaced
    g = Github(os.getenv("GITHUB_API_KEY"))

    parser = Argparser().parser
    args = parser.parse_args(namespace=Arguments)

    search_query = f"language:{args.language} fork:false "

    if args.created_after != "":
        search_query = search_query + f"created:>{args.created_after} "
    
    if args.size_min > -1 and args.size_max > -1:
        search_query = search_query + f"size:{args.size_min}..{args.size_max} "
    elif args.size_min > -1:
        search_query = search_query + f"size:>{args.size_min} "
    elif args.size_max > -1:
        search_query = search_query + f"size:<{args.size_max} "

    # search parameters: fixed language, size between min and max, created after date and no fork
    #res = g.search_repositories(query=f"language:{LANGUAGE} size:{SIZE_MIN}..{SIZE_MAX} created:>{CREATED_AFTER} fork:false")
    #query=f"language:{args.language} size:>{args.size_min} created:>{CREATED_AFTER} fork:false"
    res = g.search_repositories(query=search_query)
    print(f"Found {res.totalCount} matching repos")

    unwanted_files = ['test', '.spec.', '.d.', '.config.', '.min.']

    if args.language == 'javascript':
        dir_path = "src"
    else:
        dir_path = None

    i = 0
    while number_of_functions_in_xlsx(args) < 1000:
        repo = res[i]
        repo_path = os.sep.join([REPO_PATH, repo.name])
        if is_repo_finished(args, repo_path):
            print(repo.name, "is finished")
            continue
        print("Cloning:", repo.name)
        if not os.path.exists(repo_path):
                cloneRepo(repo.clone_url, repo_path)
        code_files = findAllFiles(args, repo_path, dir_path=dir_path)
        code_files = list(filter(lambda file: not any(keyword in file for keyword in unwanted_files), code_files))

        FunctionSplitter(args, repo.name, repo_path, code_files)
        set_repo_finished(args, repo_path)
        delete_repo_files(repo_path, repo.name)
        i = i + 1

if __name__ == "__main__":
    main()