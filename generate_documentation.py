import multiprocessing
import os
import random
import sys
import time
from time import sleep
from typing import Literal

import numpy as np
import openai
import pandas as pd
import regex as re
from dotenv import load_dotenv
from joblib import Parallel, delayed
from tqdm import tqdm

from src.utils.argparser import Argparser, Arguments

load_dotenv()

class GenerateDocumentation:

	#remove in-line comment from code
	def remove_comments_from_code(self, x, language):
		if language == "python":
			x = re.sub(re.compile("'''.*?'''", re.DOTALL), "", x)  # Remove '''...''' comments
			x = re.sub(re.compile('""".*?"""', re.DOTALL), "", x)  # Remove '''...''' comments
			x = re.sub(re.compile("(?<!(['\"]).)#[^\n]*?\n"), "\n", x)  # Remove #...\n comments
		elif language == "php":
			x = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "", x)  # Remove '''...''' comments
			x = re.sub(re.compile("\/\/[a-zA-Z0-9]+\n{1}"), "\n", x)  # Remove #...\n comments
			x = re.sub(re.compile("#[a-zA-Z0-9]+\n{1}"), "\n", x)  # Remove #...\n comments
		elif language == 'ruby':
			x = re.sub(re.compile("(?<!(['\"]).)#[^\n]*?\n"), "\n", x)  # Remove #...\n comments
		elif language == 'go':
			x = re.sub(re.compile("\/\/[a-zA-Z0-9]+\n{1}"), "\n", x)  # Remove #...\n comments
		elif language == 'javascript':
			x = re.sub(re.compile("\/\/[ a-zA-Z0-9]"), "\n", x)  # Remove #...\n comments
			x = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "", x)  # Remove '''...''' comments
		elif language == "java":
			x = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "", x)  # Remove '''...''' comments
			x = re.sub(re.compile("\/\/[a-zA-Z0-9]+\n{1}"), "\n", x)  # Remove #...\n comments	
		return x

	def documentCode(self, data):
		openai.api_key = self.api_key
		row = data[0]
		lang = data[1]
		example_code = data[2]
		example_doc = data[3]
		#lang, example_code, example_doc
		code = row['code']
		code = self.remove_comments_from_code(code,language=lang)
		example = f"""Here is an example code:
		{example_code}

		And the description should look like this:
		{example_doc}
		"""
		prompt = f"""Please document the given {lang} code like in the given example. Only return the comment
		{code}
		"""
		prompt2 = f"""Please respond with a comment describing my {lang} function.
		{code}
		"""
		prompt3 = f"""Please write a description for my function.
		{code}
		"""
		prompt4 = "Code:\n"+example_code+"\nDocumentation:\n"+example_doc+'\nCode:\n'+code+"\n"+"Documentation:\n"
		zero_shot_results = dict()
		try:
			completion = openai.ChatCompletion.create(
				model=self.MODEL,
				messages=[
				#{"role": "user", "content": example},
				{"role": "user", "content": prompt4}
				],
				temperature=0.2,
				max_tokens=256,
				top_p=1,
				frequency_penalty=0,
				presence_penalty=0,
				n = 1,
				stop=["Code:"]
			)
			comment = completion.choices[0].message.content
			#print(comment)
			return comment
		except Exception as e:
			print("Error", e)
			time.sleep(5)
			return self.documentCode(data)

	def __init__(self):
		parser = Argparser().parser
		args = parser.parse_args(namespace=Arguments)

		if args.gpt_4:
			self.api_key = os.getenv("OPENAI_GPT4_API_KEY")
			self.MODEL = "gpt-4"
			self.doc_col = 'AI documentation GPT4'
		else:
			self.api_key = os.getenv("OPENAI_API_KEY")
			self.MODEL = "gpt-3.5-turbo"
			self.doc_col = 'AI documentation'
		print("USING MODEL:", self.MODEL, ",Language:", args.language)

		if args.generated_functions:
			raw_path = os.sep.join(['data', 'raw', 'repo-samples_'+args.language+'.xlsx'])
			documentation_path = os.sep.join(['data', 'documented', "repo-documented_"+args.language+".xlsx"])
		else:
			raw_path = os.sep.join(['data', 'raw', 'samples_'+args.language+'.xlsx'])
			documentation_path = os.sep.join(['data', 'documented', "documented_"+args.language+".xlsx"])

		if os.path.exists(documentation_path):
			codesearch_df = pd.read_excel(documentation_path)
		else:
			codesearch_df = pd.read_excel(raw_path)
		
		try:
			len(codesearch_df[self.doc_col])
		except KeyError:
			codesearch_df[self.doc_col] = ""
		
		samples_path = os.sep.join(['data', 'one_shot_examples', 'samples_OneShotExample_'+args.language+'.xlsx'])

		oneshot_df = pd.read_excel(samples_path)
		example_code= oneshot_df['code'].tolist()[0]
		example_doc = oneshot_df['docstring'].tolist()[0]

		num_cores = multiprocessing.cpu_count()

		len_df = len(codesearch_df)

		try:
			current = codesearch_df[codesearch_df[self.doc_col].isna()].index[0]
		except:
			filled_len = len(codesearch_df[codesearch_df[self.doc_col] != ""])
			if filled_len == len(codesearch_df):
				print("Already finished")
				quit()
			current = 0

		print("START", current)

		if args.debug:
			quit()

		while current < (len_df - 1):
			max_index = (current+args.batch_size) -1
			if max_index > len_df - 1:
				max_index = len_df - 1
			batch_df = codesearch_df.loc[current:max_index]
			with multiprocessing.Pool(num_cores) as p:
				batch_ai_doc_list = list(tqdm(p.imap(self.documentCode, ((row, args.language,example_code, example_doc, idx) for idx,row in batch_df.iterrows())), total=len(batch_df)))
			codesearch_df.loc[current:max_index, self.doc_col] = batch_ai_doc_list

			codesearch_df.to_excel(documentation_path, index = False)
			current = max_index
			print("Done", current)

if __name__ == "__main__":
	GenerateDocumentation()