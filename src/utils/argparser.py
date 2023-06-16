import argparse
from typing import Literal, TypedDict


class Argparser:
    def __init__(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument('--language', type=str, required=True, choices=['javascript', 'java', 'python'])
        parser.add_argument('--debug', default=False, type=bool)
        parser.add_argument("--generated_functions", action=argparse.BooleanOptionalAction, default=False)
        parser.add_argument("--batch_size", type=int, default=25)

        parser_function_generator = parser.add_argument_group("function_generator")

        # set to -1 to ignore
        parser_function_generator.add_argument("--size_min", type=int, default=20000)
        parser_function_generator.add_argument("--size_max", type=int, default=-1)

        # set to "" to ignore
        parser_function_generator.add_argument("--created_after", type=str, default="2023-01-01")

        parser_documentation_generator = parser.add_argument_group("documentation_generator")
        parser_documentation_generator.add_argument("--gpt_4", action=argparse.BooleanOptionalAction, default=False)

        self.parser = parser

class Arguments(argparse.Namespace):
    language: Literal['javascript', 'java', 'python']
    generated_functions: bool
    batch_size: int
    debug: bool

    #argument group: function_generator
    size_min: int
    size_max: int
    created_after: str

    #argument group: documentation_generator
    gpt_4: bool