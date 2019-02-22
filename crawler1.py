import time
from datetime import datetime
import requests
import time
import sys
from bs4 import BeautifulSoup
import json
from pymongo import MongoClient
from bson.objectid import ObjectId #這東西再透過ObjectID去尋找的時候會用到

requests.packages.urllib3.disable_warnings()
Board=''
payload={
'from':'/bbs/'+ Board +'/index.html',
'yes':'yes' 
}

def getPageNumber(content) :
    startIndex = content.find('index')
    endIndex = content.find('.html')
    pageNumber = content[startIndex+5 : endIndex]
    return pageNumber

def checkformat(soup, class_tag, data, index, link):
    # 避免有些文章會被使用者自行刪除 標題列 時間  之類......
    try:
        content = soup.select(class_tag)[index].text
    except Exception as e:
        print('checkformat error URL', link)
        content = "no " + data
    return content
def store(data, filename):
    with open(filename, 'w') as f:
        f.write(data)
        
# python PttCrawler.py 

#####################  搜尋20推以上文章  #############################
Board = "gossiping"
start_time = time.time()
rs = requests.session()
#八卦版18禁
res = rs.post('https://www.ptt.cc/ask/over18',verify = False, data = payload)
res = rs.get('https://www.ptt.cc/bbs/'+ Board +'/index.html',verify = False)
soup = BeautifulSoup(res.text,'html.parser')
ALLpageURL = soup.select('.btn.wide')[1]['href']
ALLpage = int(getPageNumber(ALLpageURL)) + 1

URLlist=[]
fileName='PttData-'+ Board + '-' + datetime.now().strftime('%Y%m%d%H%M%S')+'.txt'

#得到每頁的所有文章
#id、title、good、author、date、url
article = -1
print("total page: " + str(ALLpage))
while ALLpage > 0 and article < 50:
    url = 'https://www.ptt.cc/bbs/'+ Board +'/index'+ str(ALLpage) +'.html'
    res = rs.get(url, verify = False)
    soup = BeautifulSoup(res.text,'html.parser')
    UrlPer = []
    for entry in soup.select('.r-ent'):
        good = entry.select('.nrec')[0].find('span')

        #保存超過20推文章的url
        if article >50: break
        if good == None or good.text[0]=="X": continue
        if good.text=="爆" or int(good.text)>20:
            title=entry.select('.title')[0].text
            title = title.replace('\n', '')
            author=entry.select('.author')[0].text
            author = author.replace('\n', '')
            date =entry.select('.date')[0].text
            atag = entry.select('.title')[0].find('a') 
            if(atag != None):
                URL = atag['href']          
                
                d = {'id': 0, 'title':title, 'good': good.text, 'author': author, 'date': date, 'url': 'https://www.ptt.cc' + URL}
                UrlPer.append(d)

    #需要反轉,因為網頁版最下面才是最新的文章
    for URL in reversed(UrlPer):
        article += 1
        URL['id']= article
        URLlist.append(URL)

    ALLpage -= 1

#####################  處理文章內容  #############################
articles=[]
for index, URL in enumerate(URLlist):
    article={}
    res = rs.get(URL["url"], verify = False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = soup.select('.bbs-screen.bbs-content')[0]
    photoIndex = 0
    article['link'] = []
    for a in content.findAll('a'):
        if a.text and a.text[-3:]=="jpg":
            article['link'].append(a.text)
            photoIndex += 1
    entry = soup.select('.article-meta-value')
    
    if len(entry)==0: continue
    article['id'] = index
    article['author'] = entry[0].text
    article['title'] = entry[2].text
    article['time'] = entry[3].text
    date = checkformat(soup, '.article-meta-value', 'date', 3, URL)
    target_content = u'※ 發信站: 批踢踢實業坊(ptt.cc),'

    content = soup.find(id="main-content").text
    
    
    content = content.split(target_content)
    
    content = content[0].split(date)
    content = content[1].replace('\n','<br/>')
#     print(content)
    article['content'] = content
    #內容
    
#        推文
    push = []
    
    for tag in soup.select('div.push'):
        if len(push) > 100: break
        # push_tag  推文標籤  推  噓  註解(→)
        push_tag = tag.find("span", {'class': 'push-tag'}).text

        # push_userid 推文使用者id
        push_userid = tag.find("span", {'class': 'push-userid'}).text
        # print "push_userid:",push_userid

        # push_content 推文內容
        push_content = tag.find("span", {'class': 'push-content'}).text
        push_content = push_content[1:]
        # print "push_content:",push_content

        # push-ipdatetime 推文時間
        push_ipdatetime = tag.find("span", {'class': 'push-ipdatetime'}).text
        push_ipdatetime = push_ipdatetime.rstrip()
        # print "push-ipdatetime:",push_ipdatetime

        push.append({"status": push_tag, "user": push_userid, "message": push_content, "message_time": push_ipdatetime});

        time.sleep(0.05) 
    article['push'] = push
    articles.append(article)
    time.sleep(0.05)     

####################################存入mlab(cloud mongodb)######

# connection
conn = MongoClient("mongodb://dominikuu:A126776091@ds213705.mlab.com:13705/article") 
db = conn['article']
collection = db['articlelist']

#文章列表
# 刪除全部舊資料 新增新資料
collection.delete_many({})
collection.insert_many(URLlist)

#文章
collection = db['articles']
collection.delete_many({})
collection.insert_many(articles)
conn.close()

collection.stats  # 如果沒有error，你就連線成功了。