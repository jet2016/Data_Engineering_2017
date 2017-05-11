#!/usr/bin/spark-submit

from os.path import expanduser
import requests
import json
import yaml
import pytz
from datetime import datetime
from dateutil.parser import parse as date_parse
from dateutil.relativedelta import relativedelta
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from time import sleep
from make_db import partition_job

#15 18 * * * /home/hadoop/pitchfork_de/code/pf_miner.py


pf_url = 'http://pitchfork.com'
base_url = 'http://pitchfork.com/reviews/albums/'
review_columns = ['artist', 'album', 'score', 'album_art', 'genre', 'label',
                'pub_date', 'abstract', 'featured_tracks', 'review_content']


def pf_croner(credentials, req_lim=20):
    ''' checks the first page for new reviews '''

    _, bucket = connect_to_s3(credentials)

    info_list = req_parse(base_url+'?page=1', req_lim) \
            .findAll("div", {"class": "review"})

    data_list = []

    # if the date cannot be parsed, that means it is new (e.g. "23 hrs ago")
    for info in info_list:
        data = req_task(pf_url+info.a['href'], req_lim)

        d = date_parse(data['pub_date'])
        datediff = relativedelta(d, pytz.utc.localize(datetime.now()))
        print(datetime.now(), d)
        if datediff.years == 0 and datediff.months == 0 and datediff.days == 0:
            print("New Review Found")
            upload_to_s3(bucket, data)
            data_list.append(data)

    partition_job(data_list, credentials)

    print("CRON Completed")


def pf_miner(credentials, limit=10000, req_lim=20):

    err_count = 0

    _, bucket = connect_to_s3(credentials)

    for page in range(1, limit):
        print("Mining page: ", page)

        info_list = req_parse(base_url+'?page={}'.format(page),
                req_lim).findAll("div", {"class": "review"})

        with ThreadPoolExecutor(max_workers=5) as executor:

            future_to_url = {executor.submit(req_task, pf_url+info.a['href'],
                    req_lim): info.a['href'] for info in info_list}

            # yields task as they are completed
            for future in as_completed(future_to_url):
                try:
                    # get the resulting data
                    data = future.result()

                except (AttributeError, TypeError):

                    err_count += 1
                    if err_count >= req_lim:
                        print('No more reviews found. Exiting...')
                        return

                    print('No more links on the page.')
                    continue
                except:
                    print('Unknown Error occurred: ', future.exception())
                    continue

                upload_to_s3(bucket, data)


def connect_to_s3(credentials, bucket_name='finalprojectpitchfork'):

    conn = S3Connection(**credentials['aws'])

    try:
        bucket = conn.get_bucket(bucket_name)
        print("Bucket found on S3")
    except:
        bucket = conn.create_bucket(bucket_name)
        print("Creating bucket")
    return conn, bucket


def upload_to_s3(bucket, data):

    try:
        k = Key(bucket)
        k.key = data['artist'] + ' - ' + data['album']
        k.set_contents_from_string(json.dumps(data, ensure_ascii=False))
        print("Uploaded ", k.key)
    except:
        print("Failed to upload", k.key)


def req_task(link, req_lim):
    '''
    calls all the functions and returns a tuple of all the review data
    '''
    print('req_task: ', link)
    soup = req_parse(link, req_lim)

    review = [get_artist(soup), get_album(soup), get_score(soup),
                get_album_art(soup), get_genres(soup), get_label(soup),
                get_pub_date(soup), get_abstract(soup),
                get_featured_tracks(soup), get_review_content(soup)]

    my_json = {}
    for col_name, item in zip(review_columns, review):
        my_json[col_name] = ''.join([c for c in item if ord(c) < 128])

    return my_json


def req_parse(link, req_lim):
    '''
    GET the link, returns None if failure. Returns the soup if all went well.
    '''
    for _ in range(req_lim):
        try:
            req = requests.get(link,headers={'User-Agent': 'Mozilla/5.0'})
            break
        except:
            print('stuck')
            sleep(5)

    # Check the page
    if req is None:
        return

    if req.status_code == 404:
        print ('There are no more pages to mine. Breaking out of loop.')
        return

    # Parse html
    soup = BeautifulSoup(req.text, 'html.parser')

    return soup


# Extractors go here
def get_artist(soup):
    try:
        return soup.findAll('h2',{'class':'artists'})[0].text.replace(":", " ").replace("/", " ")
    except:
        return ''

def get_album(soup):
    try:
        return soup.findAll('h1', {'class':'review-title'})[0].text.replace(":", " ").replace("/", " ")
    except:
        return ''

def get_score(soup):
    try:
        return soup.findAll('span',{'class':'score'})[0].text
    except:
        return ''

def get_album_art(soup):
    try:
        return soup.findAll('div',{'class':'album-art'})[0].img['src']
    except:
        return ''

def get_genres(soup):
    try:
        genres = soup.findAll('ul',{'class':'genre-list before'})
        result = ''
        for i in range(len(genres)):
            result += genres[i].text
        return result
    except:
        return ''

def get_label(soup):
    try:
        return soup.findAll('ul',{'class':'label-list'})[0].text
    except:
        return ''

def get_pub_date(soup):
    try:
        return soup.findAll('span',{'class':'pub-date'})[0]['title']
    except:
        return ''

def get_abstract(soup):
    try:
        return soup.findAll('div',{'class':'abstract'})[0].text
    except:
        return ''

def get_featured_tracks(soup):
    try:
        return soup.findAll('div',{'class':'player-display'})[0].text
    except:
        return ''

def get_review_content(soup):
    try:
        return soup.findAll('div', {'class':'contents dropcap'})[0].text.replace('\n',' ')
    except:
        return ''


if __name__ == '__main__':
    ''' Run here to CRON '''
    cred = yaml.load(open(expanduser('~/Desktop/api_cred.yml')))
    pf_croner(cred)
    #pf_miner(cred)
