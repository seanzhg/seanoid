import urllib
import requests
import bs4
import json
import getopt
import sys
from pathlib import Path


global KEY
global JSON


def post_search(keyword):
    res = requests.post(URL + '/search/', data={'keyword': keyword.encode('gb2312')})
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.content, 'html.parser')
    link_list = soup.select('.w960.center.clear.mt1 .pleft .listbox .preview')
    if link_list:
        for link in link_list:
            print(link.get('href'))


def get_search(url, param):
    global JSON
    res = requests.get(url + param)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.content, 'html.parser')
    next_param = soup.select('.w960.center.clear.mt1 .pleft .dede_pages .next')
    # link_list = soup.select('.w960.center.clear.mt1 .pleft .listbox .preview')
    link_list = soup.select('.w960.center.clear.mt1 .pleft .listbox li')
    if link_list:
        for link in link_list:
            # link_url = link.select('.preview').get('href')
            for x in link:
                if x.get("href") and x.text:
                    link_title = x.text
                    link_url = x.get("href")
                    if not JSON['mm'][KEY].get(link_title):
                        parse_webpage(link_title, link_url)
                        JSON['mm'][KEY][link_title] = link_url
    if next_param:
        get_search(url, next_param[0].get('href'))


def parse_webpage(link_title, link_url):
    url_parent = link_url[:link_url.find(Path(link_url).name) - 1]
    url_basename = ""
    res = requests.get(link_url)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text.encode("latin1").decode("gbk"), 'html.parser')
    pic_url = soup.select_one('body .content img').get("src")
    filename_suffix = Path(pic_url).name
    # filename_prefix = soup.select_one('body .content h5').text
    filename_prefix = link_title
    filename = filename_prefix + filename_suffix
    download_pic(link_url, pic_url, filename)
    nav_list = soup.select('body .content-page a')
    for nav in nav_list:
        if nav.text == "下一页":
            url_basename = nav.get("href")
    if url_basename:
        parse_webpage(link_title, url_parent + '/' + url_basename)


def download_pic(url, pic_url, file):
    global KEY
    headers = {'Referer': url, 'Sec-Fetch-Mode': 'no-cors'}
    res = requests.get(pic_url, headers=headers)
    res.raise_for_status()
    script_path = Path(__file__).parent
    download_path = script_path.joinpath('..', 'download', KEY)
    if not Path.is_dir(download_path):
        Path.mkdir(download_path)
    if not Path.exists(download_path.joinpath(file)):
        with open(str(download_path.joinpath(file)), 'wb+') as f:
            f.write(res.content)


def main(argv):
    opts, args = getopt.getopt(argv, "hl:q:", ["help", "url=", "search="])
    for o, v in opts:
        if o in ('-l', '--url'):
            url = v + "/search/"
        if o in ('-q', '--search'):
            if url.find('mm131') >= 0:
                param = "?%s" % urllib.parse.urlencode({'key': v.encode('gb2312'), 'page': 1})
                get_search(url, param)


if __name__ == '__main__':
    # main(sys.argv[1:])
    global KEY
    global JSON
    with open('download_131.json', encoding='utf-8') as f:
        JSON = json.load(f)
    for keyword in JSON['mm'].keys():
        KEY = keyword
        main(['-l', JSON['url'], '-q', keyword])
    with open('download_131.json', 'w', encoding='utf-8') as f:
        json.dump(JSON, f, ensure_ascii=False, indent=4)
