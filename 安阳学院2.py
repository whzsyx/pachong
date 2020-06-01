#coding:utf-8
import sys
from collections import deque
import urllib
from urllib import request
import re
from bs4 import BeautifulSoup
import lxml
import sqlite3
import jieba

##safelock=input('你确定要重新构建约5000篇文档的词库吗？(y/n)')
##if safelock!='y':
##    sys.exit('终止。')

url = 'http://www.pdsu.edu.cn/'  # 'http://www.zut.edu.cn'#入口

unvisited = deque()  # 待爬取链接的列表，使用广度优先搜索
visited = set()  # 已访问的链接集合
unvisited.append(url)
# unvisited.append('http://www.ayxy.edu.cn/channels/4.html')
conn = sqlite3.connect('viewsdu.db')
c = conn.cursor()
# 在create table之前先drop table是因为我之前测试的时候已经建过table了，所以再次运行代码的时候得把旧的table删了重新建
c.execute('drop table doc')
c.execute('create table doc (id int primary key,link text)')
c.execute('drop table word')
c.execute('create table word (term varchar(25) primary key,list text)')
conn.commit()
conn.close()

print('***************开始！***************************************************')
cnt = 0
print('开始。。。。。 ')
while unvisited:
    url = unvisited.popleft()
    visited.add(url)
    cnt += 1
    print('开始抓取第', cnt, '个链接：', url)

    # 爬取网页内容
    try:
        response = request.urlopen(url)
        content = response.read().decode('utf-8')

    except:
        continue

    # 寻找下一个可爬的链接，因为搜索范围是网站内，所以对链接有格式要求，这个格式要求根据具体情况而定

    # 解析网页内容,可能有几种情况,这个也是根据这个网站网页的具体情况写的
    soup = BeautifulSoup(content, 'lxml')
    all_a = soup.find_all('a',{"li":"line_u5_0"})  # 本页面所有的新闻链接<a>
    for a in all_a:
        # print(a.attrs['href'])
        x = a.attrs['href']  # 网址
        if re.match(r'http.+', x):  # 排除是http开头，而不是http://www.zut.edu.cn网址
            if not re.match(r'http\:\/\/www\.pdsu\.edu\.cn\/.+', x):
                continue
        if re.match(r'\/info\/.+', x):  # "/info/1046/20314.htm"
            x = 'http://www.pdsu.edu.cn/' + x
        elif re.match(r'info/.+', x):  # "info/1046/20314.htm"
            x = 'http://www.pdsu.edu.cn/' + x
        elif re.match(r'\.\.\/info/.+', x):  # "../info/1046/20314.htm"
            x = 'http://www.ayxy.edu.cn' + x[2:]
        elif re.match(r'\.\.\/\.\.\/info/.+', x):  # "../../info/1046/20314.htm"
            x = 'http://www.pdsu.edu.cn/' + x[5:]
        # print(x)
        if (x not in visited) and (x not in unvisited):
            unvisited.append(x)

    a = soup.find('a', {'class': "Next"})  # 下一页<a>
    if a != None:
        x = a.attrs['href']  # 网址
        if re.match(r'xwdt\/.+', x):
            x = 'http://news.pdsu.edu.cn/info/1029/30287.htm' + x
        else:
            x = 'http://www.ayxy.edu.cn/channels/7130.html' + x
        if (x not in visited) and (x not in unvisited):
            unvisited.append(x)

    title = soup.title
    article = soup.find('div', class_='c67215_content', id='vsb_newscontent')
    author = soup.find('span', class_="authorstyle67215")  # 作者
    time = soup.find('span', class_="timestyle67215")
    if title == None and article == None and author == None:
        print('无内容的页面。')
        continue

    elif article == None and author == None:
        print('只有标题。')
        title = title.text
        title = ''.join(title.split())
        article = ''
        author = ''

    elif article == None:
        print('有标题有作者，缺失内容')
        title = title.text
        title = ''.join(title.split())
        article = ''
        author = author.get_text("", strip=True)
        author = ''.join(author.split())

    elif author == None:
        print('有标题有内容，缺失作者')
        title = title.text
        title = ''.join(title.split())
        article = article.get_text("", strip=True)
        article = ''.join(article.split())
        author = ''
    else:
        title = title.text
        title = ''.join(title.split())
        article = article.get_text("", strip=True)
        article = ''.join(article.split())
        author = author.get_text("", strip=True)
        author = ''.join(author.split())

    print("网页标题：", title)

    # 提取出的网页内容存在title,article,author三个字符串里，对它们进行中文分词
    seggen = jieba.cut_for_search(title)
    seglist = list(seggen)
    seggen = jieba.cut_for_search(article)
    seglist += list(seggen)
    seggen = jieba.cut_for_search(author)
    seglist += list(seggen)

    # 数据存储
    conn = sqlite3.connect("viewsdu.db")
    c = conn.cursor()
    c.execute('insert into doc values(?,?)', (cnt, url))

    # 对每个分出的词语建立词表
    for word in seglist:
        # print(word)
        # 检验看看这个词语是否已存在于数据库
        c.execute('select list from word where term=?', (word,))
        result = c.fetchall()
        # 如果不存在
        if len(result) == 0:
            docliststr = str(cnt)
            c.execute('insert into word values(?,?)', (word, docliststr))
        # 如果已存在
        else:
            docliststr = result[0][0]  # 得到字符串
            docliststr += ' ' + str(cnt)
            c.execute('update word set list=? where term=?', (docliststr, word))

    conn.commit()
    conn.close()
print('词表建立完毕=======================================================')
