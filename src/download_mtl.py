import requests
import bs4
import json
import time
import string
import logging
from pathlib import Path


logging.basicConfig(level=logging.DEBUG)
global JSON


def get_page(url):
    res = None
    try:
        res = requests.get(url)
        res.raise_for_status()
    except Exception as e:
        time.sleep(10)
        try:
            res = requests.get(url)
            res.raise_for_status()
        except Exception as e:
            logging.exception("Exception: %s" % e)
            print("%s could not be found" % url)
    return res


def soup_page(url):
    soup = None
    res = get_page(url)
    if res:
        soup = bs4.BeautifulSoup(res.content, 'html.parser')
    return soup


def update_category(url):
    global JSON
    soup = soup_page(JSON['url'])
    cats = soup.select('body .header .top .nav .menu #tag_ul li')
    for cat in cats:
        cat_title = cat.text
        cat_url = cat.a.get('href')
        if cat_title not in JSON['category']:
            JSON['category'][cat_title] = {}
        JSON['category'][cat_title]['home_page'] = cat_url
    

def download_category(cat):
    global JSON
    url = JSON['category'][cat]['home_page']
    walk_through_page(url, JSON['category'][cat].get('skip_on_first_match', False))
    JSON['category'][cat]['skip_on_first_match'] = True


def walk_through_page(url, skip):
    logging.info(url)
    soup = soup_page(url)
    if not soup:
        return
    list_box = soup.select('body .main .boxs .img li > a')
    for item in list_box:
        if item.get('href') and item.img.get('alt'):
            page_title = item.img.get('alt')
            page_url = item.get('href')
            ret = download_album(page_title, page_url)
            if ret == "Skip" and skip is True:
                return
    if skip is False:
        nav_list = soup.select('body .main center a')
        for item in nav_list:
            if item.text == "下一页" and url.find(item.get('href')) < 0:
                if item.get('href').startswith("http://www.meitulu.com"):
                    next_page = item.get('href')
                else:
                    next_page = "http://www.meitulu.com" + item.get('href')
                walk_through_page(next_page, skip)
                break


def download_album(link_title, link_url):
    """
    Error: 下载失败
    Skip: 跳过
    Success: 下载成功
    """
    global JSON
    logging.debug("%s start" % link_url)
    soup = soup_page(link_url)

    if soup is None:
        logging.error("%s error" % link_url)
        return "Error"

    model_info = soup.select('body .width .c_l p')
    model_name = None
    model_url = None
    for item in model_info:
        if item.text.find('模特姓名') >= 0:
            try:
                model_name = item.a.text.translate(str.maketrans("", "", string.punctuation + string.whitespace))
                model_url = item.a.get('href')
            except:
                model_name = item.text[item.text.find('：') + 1:].translate(str.maketrans("", "", string.punctuation + string.whitespace))
                model_url = None
            if model_name == '':
                model_name = '未名'
            break
    if not model_name:
        model_name = '未名'
    if model_name not in JSON['mm']:
        JSON['mm'][model_name] = {}
        JSON['mm'][model_name]['favorite'] = True
    else:
        JSON['mm'][model_name]['favorite'] = check_model_in_followinglist(model_name)
    if not JSON['mm'][model_name].get('favorite'):
        JSON['mm'][model_name]['list'] = {}
        return "Skip"
    JSON['mm'][model_name].update({'home_page': model_url})
    if 'list' not in JSON['mm'][model_name]:
        JSON['mm'][model_name]['list'] = {}
    if link_title in JSON['mm'][model_name]['list']:
        logging.debug("%s skip" % link_url)
        return "Skip"

    logging.debug("%s download" % link_url)
    pic_info = soup.select('body .content center img')
    for item in pic_info:
        pic_url = item.get("src")
        filename_suffix = Path(pic_url).name
        filename_prefix = link_title
        filename = filename_prefix + filename_suffix
        download_pic(pic_url, model_name, filename)

    next_page = ""
    nav_list = soup.select('body > center a')
    for nav in nav_list:
        if nav.text == "下一页":
            next_page = JSON['url'] + nav.get("href")
    if next_page and next_page != link_url:
        download_album(link_title, next_page)

    JSON['mm'][model_name]['list'][link_title] = link_url
    with open('download_mtl.json', 'w', encoding='utf-8') as f:
        json.dump(JSON, f, ensure_ascii=False, indent=4)

    print("%s end" % link_url)
    return "Success"


def check_model_in_followinglist(model):
    """
    已下载的以模特名称命名的目录若被删除，就不再下载更新的专辑
    """
    global JSON
    script_path = Path(__file__).parent
    download_path = script_path.joinpath('..', '..', 'download', model)
    if not Path.is_dir(download_path):
        return False
    return True


def download_pic(url, model, file):
    global JSON
    res = get_page(url)
    if res:
        script_path = Path(__file__).parent
        download_path = script_path.joinpath('..', '..', 'download', model)
        if not Path.is_dir(download_path):
            Path.mkdir(download_path)
        try:
            if not Path.exists(download_path.joinpath(file)):
                with open(str(download_path.joinpath(file)), 'wb+') as f:
                    f.write(res.content)
        except:
            logging.error("failed to save %s %s %s" % (url, model, file))
            file = file.translate(str.maketrans('/<>~|!?', "       ", ""))
            logging.error("save as %s %s %s" % (url, model, file))
            with open(str(download_path.joinpath(file)), 'wb+') as f:
                f.write(res.content)


def main():
    global JSON
    update_category(JSON['url'])
    for cat in JSON['category']:
        download_category(cat)


if __name__ == '__main__':
    # main(sys.argv[1:])
    global JSON
    with open('download_mtl.json', encoding='utf-8') as f:
        JSON = json.load(f)
    main()
    with open('download_mtl.json', 'w', encoding='utf-8') as f:
        json.dump(JSON, f, ensure_ascii=False, indent=4)
