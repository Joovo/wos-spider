工作上需要爬取 wos 的一些专利号和施引专利，做成了一个 excel 表格。施引专利在系统默认的导出里是没有的。
第一次实际运用了`concurrent.futures` 来处理并发下载，确实很简单。一开始用 `scrapy` 框架貌似连接非常慢，不知道什么原理，三次连接两次超时，于是手写了一个用很多 try/except 结构的 spider 。

**一定要记得写日志和异常处理！！！！**
全文基本上没有很难的地方，主要是坑
- wos有时候会返回一个加载的页面，也怀疑是请求超时导致的，这时候需要重复 `requests.get()`
- 解析施引专利的时候会根据情况遇到两种`xpath`，都需要考虑
- 不需要考虑对文件加锁，并发下载本来就不应该使用同一个文件指针，如果一定要用就在线程结束的时候写入，而不是考虑阻塞线程。

伪代码：
```
zlh： 专利号
syzl： 施引专利
def main_crawl():
    构造page的url
    for 每个 page:
        下载页面
        解析专利号
        if 专利号没有完全显示:
            获取专利号详情页链接
            zlh_crawl()
        解析施引专利
        储存到临时列表
    将临时列表写入文件

def zlh_crawl():
    下载专利号详情页
    解析专利号
```
## wos_spider.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
zlh： 专利号
syzl： 施引专利

用concurrent.futures 处理并发,第一个参数为调用对象（函数），第二个参数为可迭代对象
'''

import requests
from lxml import etree
from concurrent import futures
import time
from datetime import datetime


def main_crawl(page):
    sid = '6AYdysu8mvLaGzw8Exb'
    url = "http://apps.webofknowledge.com/summary.do"

    querystring = {"product": "DIIDW", "colName": "DIIDW", "qid": "5", "SID": sid,
                   "search_mode": "GeneralSearch", "formValue(summary_mode)": "GeneralSearch",
                   "update_back2search_link_param": "yes", "page": page, "isCRHidden": "true"}

    headers = {
        'cache-control': "no-cache",
    }
    # 初始化错误信息
    error_page = page
    error = False
    _file = []
    s = requests.Session()
    try:
        r = s.request("GET", url, headers=headers, params=querystring)
        r.encoding = r.apparent_encoding
        tree = etree.HTML(r.text)
        max_index = 51
        # 最后一页只有41项
        if page == 292:
            max_index = 41
        for recode_num in range(1, max_index):
            # 构造 recode_num
            # 开始解析专利号
            num = (page - 1) * 50 + recode_num
            zlh_xpath = '//*[@id="RECORD_' + str(num) + '"]/div[3]/text()'
            # //*[@id="RECORD_51"]/div[3]/text()
            # //*[@id="RECORD_14551"]/div[3]/text()
            # 如果页面出错，重复请求
            while (True):
                try:
                    zlh = tree.xpath(zlh_xpath)[0]
                    break
                except:
                    r = s.request("GET", url, headers=headers,params=querystring)
                    r.encoding = r.apparent_encoding
                    tree = etree.HTML(r.text)
            # 如果最后一项是 . 进入该专利详情进行爬取
            if zlh[-1] == '.':
                item_url_xpath = '//*[@id="RECORD_' + \
                    str(num) + '"]/div[3]/div[2]/div/a/@href'
                item_url = 'http://apps.webofknowledge.com' + \
                    tree.xpath(item_url_xpath)[0]
                zlh = zlh_crawl(s, item_url) # 进入详情页

            # 开始解析施引专利，有两种情况，用 try结构
            try:
                syzl_num_xpath = '//*[@id="RECORD_' + \
                    str(num) + '"]/div[3]/div[1]/value/text()'
                # //*[@id="RECORD_101"]/div[3]/div[1]/value
                syzl_num = tree.xpath(syzl_num_xpath)[0]
            except:
                syzl_num_xpath = '//*[@id="RECORD_' + \
                    str(num) + '"]/div[3]/div[1]/a/value/text()'
                # //*[@id="RECORD_101"]/div[3]/div[1]/a/value
                syzl_num = tree.xpath(syzl_num_xpath)[0]
            finally:
                print(zlh + ' ' + syzl_num)
                _file.append(zlh + ' ' + syzl_num) # 保存该页面的各项信息
                print(_file)
    except e:# 处理报错信息
        error_num = num
        error = True
    finally:
        with open('wos2.txt', 'a', encoding='utf-8') as file:
            for i in _file:
                file.write('{}\n'.format(i)) # 保存该页面的各项信息
        if error is True:
            with open('log.txt', 'a', encoding='utf-8') as e:
                e.write('page {} find error,error_num is {}.Time is {}\n'.format(error_page, error_num,datetime.now().strftime('%b-%d-%Y %H:%M:%S')))

def zlh_crawl(s, url):
    zlh_response = s.get(url)
    zlh_response.encoding = zlh_response.apparent_encoding
    tree = etree.HTML(zlh_response.text)
    zlh_xpath = '//*[@id="FullRecDataTable"]/tr[2]/td/text()'
    zlh_list = tree.xpath(zlh_xpath)
    zlh = ''
    for i in zlh_list:
        zlh += i
    return zlh


if __name__ == '__main__':
    t1 = time.time() # 开始时间
    with futures.ThreadPoolExecutor(max_workers=4) as e:
        e.map(main_crawl, range(1, 293)) # 类似 map 用法
    t2 = time.time() # 结束时间
    # 打印日志
    with open('log.txt', 'a', encoding='utf-8') as l:
        l.write('spider cost {}s.Time is {}.\n'.format(t2 - t1, datetime.now().strftime('%b-%d-%Y %H:%M:%S')))

```

## txt2excel.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
xlwt：创建excel的库
sheet.write(行坐标，列坐标，字符串等)
读取txt文件的每一行，每行字符串用空格划分
最后一项为施引专利储存在第2列
其余为专利号放第一列
'''
import xlwt

if __name__ == '__main__':
    wbk = xlwt.Workbook() # 创建文件
    sheet = wbk.add_sheet('sheet1')
    sheet.write(0,0,'专利号')
    sheet.write(0,1,'施引专利')
    row = 1

    with open('./wos_test.txt', 'r') as file:
        for i in file.readlines(): # 读取每一行
            lst = i.split() # 用空格划分
            s = ''
            for i in range(len(lst)-1): # 除最后一列
                s += str(lst[i])
            sheet.write(row, 0, s)
            sheet.write(row, 1, lst[-1])
            row += 1 # 行坐标+1
        wbk.save('wos.xls')

```
## log.txt
```
spider cost 866.1539652347565s.Time is Oct-06-2018 16:05:20.
spider cost 12755.609891653061s.Time is Oct-06-2018 19:52:53.

```
