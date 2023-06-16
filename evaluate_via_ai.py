import multiprocessing
import os
import re

import numpy as np
import openai
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from tqdm import tqdm

from src.utils.argparser import Argparser, Arguments

load_dotenv()

class EvaluateDocumentation:

	def get_rating(self, comment: str, code: str, n_try: int = 1):
		openai.api_key = self.api_key
		data_prompt = f"""Code:
		{code}

		Documentation:
		{comment}
		"""
		try:
			completion = openai.ChatCompletion.create(model="gpt-3.5-turbo",
				temperature=0,
				messages=[
				{"role": "user", "content": data_prompt},
				{"role": "user", "content": self.SECOND_PROMPT2}
				]
				)
			rating = completion.choices[0].message.content
			#print(rating)
			digits = re.findall(r'\b\d+\b', rating)
			return int(digits[0])
		except:
			if (n_try >= 10):
				return -1
			return self.get_rating(comment, code, n_try=n_try+1)

	def prepare_comment(self, comment:str)-> str:
		comment = str(comment).lstrip().rstrip()
		comment = comment.split(".")[0] + "."
		return comment

	def rate_code(self, row):
			code = row['code']

			try:
				ref_doc = self.prepare_comment(row['docstring'])
				ref_rating = self.get_rating(ref_doc, code)
			except KeyError as e:
				ref_rating = -1

			try:
				pred_doc_gpt4 = self.prepare_comment(row['AI documentation GPT4'])
				gpt_3_rating = self.get_rating(pred_doc_old, code)
			except KeyError as e:
				gpt_3_rating = -1

			try:
				pred_doc_gpt3_5 = self.prepare_comment(row['AI documentation'])
				gpt_3_5_rating = self.get_rating(pred_doc_gpt3_5, code)
			except KeyError as e:
				gpt_3_5_rating = -1

			try:
				pred_doc_old = self.prepare_comment(row['GPT-3 documentation'])
				gpt_4_rating = self.get_rating(pred_doc_gpt4, code)
			except KeyError as e:
				gpt_4_rating = -1
			
			return {
				'ref': ref_rating,
				'gpt_3': gpt_3_rating,
				'gpt_3.5': gpt_3_5_rating,
				'gpt_4':gpt_4_rating
			}
	
	def evaluate_ratings(self, df: pd.DataFrame):

		ratings_ref = df[self.col_rating_ref]
		ratings_gpt_3 = df[self.col_rating_gpt_3]
		ratings_gpt_3_5 = df[self.col_rating_gpt_3_5]
		ratings_gpt_4 = df[self.col_rating_gpt_4]

		print('Ref, Count invalid ratings', len(ratings_ref[ratings_ref == -1]))
		print('Pred GPT 3, Count invalid ratings', len(ratings_gpt_3[ratings_gpt_3 == -1]))
		print('Pred GPT 3.5, Count invalid ratings', len(ratings_gpt_3_5[ratings_gpt_3_5 == -1]))
		print('Pred GPT 4, Count invalid ratings', len(ratings_gpt_4[ratings_gpt_4 == -1]))

		ratings_ref = ratings_ref[ratings_ref > -1]
		ratings_gpt_3 = ratings_gpt_3[ratings_gpt_3 > -1]
		ratings_gpt_3_5 = ratings_gpt_3_5[ratings_gpt_3_5 > -1]
		ratings_gpt_4 = ratings_gpt_4[ratings_gpt_4 > -1]

		print('Ref', np.mean(ratings_ref))
		print('Pred GPT 3',np.mean(ratings_gpt_3))
		print('Pred GPT 3.5',np.mean(ratings_gpt_3_5))
		print('Pred GPT 4',np.mean(ratings_gpt_4))

		#Null Hypothesis (H0): Dependent sample means (m1 and m2) are equal (m1=m2).
		#Alternative Hypothesis (Ha): Dependent sample means (m1 and m2) are not equal (m1!=m2)
		#print("Ref vs GPT 3.5", stats.ttest_rel(ratings_ref, ratings_gpt_3_5))
		#print("Ref vs GPT 4", stats.ttest_rel(ratings_ref, ratings_gpt_4))
		#print("GPT 3.5 vs GPT 4", stats.ttest_rel(ratings_gpt_3_5, ratings_gpt_4))
		#Reject the null hypothesis if p-value <= alpha
		#Fail to reject the null hypothesis if p-value > alpha


	def __init__(self):

		parser = Argparser().parser
		args = parser.parse_args(namespace=Arguments)

		self.SECOND_PROMPT = """Please rate the quality of the comment by only answering with a number between 0 and 100."""
		self.SECOND_PROMPT2 = """Please rate the documentation for the given code by only answering with a number between 0 and 100."""

		self.api_key = os.getenv("OPENAI_GPT4_API_KEY")

		if args.generated_functions:
			documentation_path = os.sep.join(['data', 'documented', "repo-documented_"+args.language+".xlsx"])
		else:
			documentation_path = os.sep.join(['data', 'documented', "documented_"+args.language+".xlsx"])

		codesearch_df = pd.read_excel(documentation_path)

		len_df = len(codesearch_df)

		self.col_rating_ref = 'Rating Ref'
		self.col_rating_gpt_3 = 'Rating GPT 3'
		self.col_rating_gpt_3_5 = 'Rating GPT 3.5'
		self.col_rating_gpt_4 = 'Rating GPT 4'

		try:
			len(codesearch_df[self.col_rating_ref])
		except KeyError:
			codesearch_df[self.col_rating_ref] = ""

		try:
			current = codesearch_df[codesearch_df[self.col_rating_ref].isna()].index[0]
		except:
			filled_len = len(codesearch_df[codesearch_df[self.col_rating_ref] != ""])
			if filled_len == len(codesearch_df):
				print("Already finished")
				self.evaluate_ratings(codesearch_df)
				quit()
			current = 0

		print("START", current)
		if args.debug:
			quit()

		num_cores = multiprocessing.cpu_count()

		while current < (len_df - 1):
			max_index = (current+args.batch_size) -1
			if max_index > len_df - 1:
				max_index = len_df - 1
			batch_df = codesearch_df.loc[current:max_index]
			with multiprocessing.Pool(num_cores) as p:
				rating_list = list(tqdm(p.imap(self.rate_code, ((row) for idx,row in batch_df.iterrows())), total=len(batch_df)))
			rating_list_ref = []
			rating_list_gpt_3 = []
			rating_list_gpt_3_5 = []
			rating_list_gpt_4 = []
			for rating in rating_list:
				rating_list_ref.append(rating['ref'])
				rating_list_gpt_3.append(rating['gpt_3'])
				rating_list_gpt_3_5.append(rating['gpt_3.5'])
				rating_list_gpt_4.append(rating['gpt_4'])
			codesearch_df.loc[current:max_index, self.col_rating_ref] = rating_list_ref
			codesearch_df.loc[current:max_index, self.col_rating_gpt_3] = rating_list_gpt_3
			codesearch_df.loc[current:max_index, self.col_rating_gpt_3_5] = rating_list_gpt_3_5
			codesearch_df.loc[current:max_index, self.col_rating_gpt_4] = rating_list_gpt_4

			codesearch_df.to_excel(documentation_path, index = False)
			current = max_index
			print("Done", current)
		self.evaluate_ratings(codesearch_df)
		#with multiprocessing.Pool(num_cores) as p:
		#	rating_list = list(tqdm(p.imap(self.rate_code, ((row) for idx,row in codesearch_df.iterrows())), total=len(codesearch_df)))

		#print('Ref', np.mean(rating_list_ref))
		#print('Pred new ',np.mean(rating_list_pred))
		#print('Pred old',np.mean(rating_list_pred_old))
		#Ref 78.525
		#Pred new  83.425
		#Pred old 78.225

		"""
		Javascript all 1000 gpt-3.5-turbo:
		Ref 79.23
		Pred new  83.815
		Pred old 76.925

		Python all 1000 gpt-3.5-turbo:
		Ref 79.475
		Pred new  84.895
		Pred old 81.2
		"""


if __name__ == "__main__":
		EvaluateDocumentation()