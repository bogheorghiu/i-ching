import sys, json, os, time, hashlib, urllib.request
sys.path.insert(0,'/home/user/wt-research/research')
import keys
def fetch(url):
    return keys._post("https://api.deepseek.com/v1/tools/fetch","DEEPSEEK_API_KEY",{"url":url},timeout=120)
def search(q,count=10,need=False):
    return keys._post("https://api.deepseek.com/v1/tools/search","DEEPSEEK_API_KEY",{"query":q,"count":count,"need_content":need})
