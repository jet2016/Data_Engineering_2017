from os.path import expanduser
import json
import yaml
import psycopg2
from pyspark import SparkContext

# Run this on EMR. Make sure to install psycopg2

global my_cred


def spark_job(sc, bucket_path):
	rdd = sc.textFile(bucket_path)
	print("Distributing jobs to partitions")
	rdd.foreachPartition(partition_job)
	print("All partition jobs completed. Exiting...")


def partition_job(source, credentials=None):

	if not credentials:
		credentials = my_cred.value

	conn, cur = connect_to_psql(credentials)

	query = """INSERT INTO reviews (artist, album, score, album_art, genre, label,
                pub_date, abstract, review_content)
                VALUES (%(artist)s, %(album)s, %(score)s, %(album_art)s, %(genre)s,
                %(label)s, %(pub_date)s, %(abstract)s, %(review_content)s)"""

	print("Starting job...")

	for item in source:

		try:
			if type(item) == unicode:
				data = json.loads(item)
			elif type(item) == dict:
				data = item
				print('Inserting album: ', data['album'])
			cur.execute(query, data)
		except:
			conn.rollback()

		conn.commit()

	print("Partition job completed.")


def make_table():

	conn, cur = connect_to_psql()

	query = """CREATE TABLE IF NOT EXISTs reviews
				(id SERIAL PRIMARY KEY, artist varchar(255), album varchar(255),
				 score varchar(255), album_art varchar(255), genre varchar(255),
				 label varchar(255), pub_date TIMESTAMP, abstract TEXT,
				 featured_tracks varchar(255), review_content TEXT)"""
	try:
	    cur.execute(query)
	except:
	    print("Something bad happenned while making tables...?")

	conn.commit()
	print("Finished creating reviews table.")


def connect_to_psql(credentials=None):

	if not credentials:
		credentials = my_cred.value

	try:
		print("Connecting...")
		conn = psycopg2.connect(**credentials['rds'])
		cur = conn.cursor()
		print("Connection Established")
	except:
		print("Error Establishing Connection (bad credentials?)")
		return False

	return conn, cur


if __name__ == "__main__":
	sc = SparkContext()
	my_cred = sc.broadcast(yaml.load(open(expanduser('~/Desktop/api_cred.yml'))))
	make_table()
	spark_job(sc, "s3a://finalprojectpitchfork/*")
