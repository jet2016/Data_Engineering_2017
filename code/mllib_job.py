import shutil
import json
import pickle
from collections import Counter
from pyspark import SparkContext
from pyspark.mllib.linalg import SparseVector
from pyspark.mllib.regression import LabeledPoint
from pyspark.mllib.evaluation import BinaryClassificationMetrics
from pyspark.mllib.classification import NaiveBayes, NaiveBayesModel

'''
Use spark-submit for this script
see https://davefernig.com/2016/05/07/building-a-term-document-matrix-in-spark/
'''

sc = SparkContext()

stopwords = sc.broadcast(open('../stopwords.txt', 'r').read().split('\n'))
stopwords.value.append('')


def jsonify(review):
	return json.loads(review.encode('ascii', 'ignore'))


def tokenize(review):
	try:
		tokens = review['review_content'].split(' ')
		tokens = [w.strip().lower() for w in tokens]
		review['review_content'] = [w for w in tokens if w not in stopwords.value]
	except:
		review['review_content'] = []
	return review


bucket_path = "s3a://finalprojectpitchfork/*"


corpus = sc.textFile(bucket_path)

# parse the original strings as json
jsonified_corpus = corpus.map(jsonify)

# parse the review into words. Repartition to improve performance
tokenized_corpus = jsonified_corpus.map(tokenize).repartition(100).cache()


# label each word with some number to keep track of their column num.
local_vocab_map = tokenized_corpus \
    .flatMap(lambda rev: rev['review_content']) \
    .distinct() \
    .zipWithIndex() \
    .collectAsMap()

vocab_map = sc.broadcast(local_vocab_map)
inv_vocab_map = sc.broadcast({v: k for k, v in vocab_map.value.items()})
vocab_size = sc.broadcast(len(local_vocab_map))
vocab_counts = sc.broadcast({key: sc.accumulator(0) for key, _ in vocab_map.value.items()})


def agg_counts(review):
	pairs = []
	for k, v in Counter(review['review_content']).items():
		pairs.append((k, v))
	return pairs

word_count = tokenized_corpus \
			.flatMap(agg_counts) \
			.reduceByKey(lambda x, y: x+y) \
			.collect()

with open('../app/static/word_count.txt', 'wb') as f:
	pickle.dump(word_count, f)


# score above 8.2 is Best New Music (label 1), otherwise label 0
def build_one_row_of_matrix(review_tuple):
	if review_tuple[0] >= 8.2:
		score = 1.0
	else:
		score = 0.0
	sparse_row = {}
	for token in review_tuple[1]:
		sparse_row[vocab_map.value[token]] = float(review_tuple[1][token])
	return LabeledPoint(score, SparseVector(vocab_size.value, sparse_row))

# build term frequency matrix, with labels, which are the scores
term_freq_matrix = tokenized_corpus \
    .map(lambda rev: (rev['score'], Counter(rev['review_content']))) \
    .map(build_one_row_of_matrix)

# see https://spark.apache.org/docs/2.1.0/mllib-naive-bayes.html
train_set, test_set = term_freq_matrix.randomSplit([0.6, 0.4])

model = NaiveBayes.train(train_set, 1.0)

predictionAndLabel = test_set.map(lambda p: (model.predict(p.features), p.label))
accuracy = 1.0 * predictionAndLabel.filter(lambda (x, v): x == v).count() / test_set.count()
print('model accuracy {}'.format(accuracy))

# save the model
output_dir = 's3a://finalprojectmachinelearning/naivebayes'
shutil.rmtree(output_dir, ignore_errors=True)
model.save(sc, output_dir)
