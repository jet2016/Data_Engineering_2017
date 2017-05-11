from os import path
import json
import pickle
from PIL import Image
import numpy as np
from wordcloud import WordCloud, STOPWORDS

'''Jobs for making the word cloud'''

def main():
	with open('./static/word_count.txt', 'rb') as f:
		word_count = pickle.load(f)
		make_wc(np.array(Image.open(path.join(d, "./static/pf_logo.jpg"))),
				stringify(word_count))


def make_wc(mask, text):

	stopwords = set(STOPWORDS)
	stopwords.add("said")

	wc = WordCloud(background_color="white", max_words=2000, mask=mask, stopwords=stopwords)

	# generate word cloud
	wc.generate(text)

	# store to file
	wc.to_file(path.join(d, "./static/pf_wc.jpg"))


def stringify(word_count):
	s = ''
	stopwords = set(STOPWORDS)
	stopwords.add("said")
	for w, c in word_count:
		if w in stopwords or len(w) < 3:
			continue
		else:
			for i in range(c):
				s+=w
	with open('static/words.txt', 'w') as f:
		f.write(s)
	return s
