import elasticsearch
from jproperties import Properties

from elasticsearch import Elasticsearch
import pandas as pd
import numpy as np

def create_es_connection():
    config = Properties()

    with open('elastic_search_config.prop','rb') as f:
        config.load(f)

    es = Elasticsearch([{'host':config.get('endpoint').data,
                        'port':config.get('port').data}])
    
    return es

def search_word(search_phrase,number,field):

  # product-name
    words = search_phrase.split(" ")
    json = []
    size = str(number+20)
    for word in words:
        query = {
            "_source":["product-name","product-number","category","sub-category","image-path","_id"],
            "size":size,
            "query":{
                "match":{
                    field: word
                }
            }
        }
        es = create_es_connection()
        json.append(es.search(index="product-level", doc_type="_doc",body=query))

    return json

def search_phrases(search_phrase,number,field):

    size = str(number+20)
    query = {
        "_source":["product-name","product-number","category","sub-category","image-path","_id"],
        "size":size,
        "query":{
            "match_phrase":{
                field: search_phrase
            }
        }
    }
    es = create_es_connection()
    json=es.search(index="product-level", doc_type="_doc",body=query)

    p_id = []
    score =[]

    if len(json['hits']['hits'])>0:
        p_id = json['hits']['hits'][0]['_source']['product-number']
        score = json['hits']['hits'][0]['_score']
        search_phrase_value = pd.DataFrame(pd.Series({'product-number':p_id,'score':score})).T
        return search_phrase_value
    else:
        return pd.DataFrame({'product-number':p_id,'score':score})
    

def agg_json(json_field):
    p_id = []
    score = []
    for file in json_field:
      #print(file)
      for record in file['hits']['hits']:
        p_id.append(record['_source']['product-number'])
        score.append(record['_score'])
    prod_no = pd.DataFrame({'product-number':p_id,"score":score})
    #prod_no.sort_values(by='index_id',inplace=True)
    #prod_no['product-number']=df[df['level_0'].isin(prod_no['index_id'])]['product-number'].values
    prod_no = prod_no.groupby('product-number').agg(sum).reset_index(drop = False).sort_values('score',ascending=False)
    #print(prod_no.info())
    #print(score)
    #print(p_id)
    return prod_no

def call_field(search_phrase, number):

    fields = ['product-name','category','sub-category']
    json_field = []
    for field in fields:
        json_field.append(search_word(search_phrase,number,field))
    #print(json_field[0][1])
    #print([len(json_field)])
    #print([len(json_field[i]) for i in range(3)])
    #return json_field
  
    prod_no = agg_json(json_field[0])
    #print(prod_no)
    category = agg_json(json_field[1])
    sub_category = agg_json(json_field[2])

    return prod_no, category,sub_category


def call_functions(search_phrase1,number):
  
    prod_no1, category1,sub_category1 = call_field(search_phrase1,number)
    search_phrase_value = search_phrases(search_phrase1,number,'product-name')

    return prod_no1, category1,sub_category1,search_phrase_value


def score(prod_no,category,sub_category,search_phrase,a,b,c,d):
    prod_no['score'] = a*prod_no['score']
    category['score'] = b*category['score']
    sub_category['score'] = c*sub_category['score']
    search_phrase['score'] = d*search_phrase['score']

    interim = prod_no.merge(category, how='outer',on='product-number')
    interim1 = interim.merge(sub_category,how='outer',on='product-number')
    interim1.rename(columns={'score_x':'product-name','score_y':'category','score':'sub-category'},inplace=True)
    final = interim1.merge(search_phrase,how='outer',on='product-number',)

    final.fillna(0,inplace=True)
    final['score_final'] = final['product-name']+final['category']+final['sub-category']+final['score']
    final.sort_values(by='score_final', ascending=False,inplace=True)
    final = final.iloc[:20]
    return final


def recommendations_for_textsearch_query(query, number=10):
    obj =prod_no1, category1,sub_category1,search_phrase_value = call_functions(query,number)
    # Flag for result not being empty
    bina = np.array([1 if len(x) > 0 else 0 for x in obj])
    # Weights for the productname, category, sub category, search phrases
    probability = np.array([0.35,0.04,0.01,0.60])
    revised_prob = probability* bina
    revised_prob = revised_prob/sum(revised_prob)
    
    frame = score(prod_no1,category1,sub_category1,search_phrase_value,*revised_prob)
    return frame

