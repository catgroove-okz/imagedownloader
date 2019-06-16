import sys

from os import environ
from time import sleep
from pathlib import Path
from argparse import ArgumentParser
from requests_html import HTMLSession
from urllib.parse import urlparse, unquote


save_path = Path(environ['HOME']) / 'images'
file_ext = ('.jpg', '.gif')
INTERVAL_SLEEP = 3
# /path/to/domain/article_title or /path/to/domain/params
use_directoryname_title = True


def fetch_link(url):
    session = HTMLSession()
    session.headers.update(
        {"referer": url,
         "User-Agent": 'Mozilla/5.0 (X11; Linux x86_64) \
         AppleWebKit/537.36 (KHTML, like Gecko) \
         Chrome/75.0.3770.80 Safari/537.36'})
    response = session.get(url, timeout=1, stream=True)
    if response.status_code == 200:
        return response
    return False


def _to_parse(url):
    r = urlparse(url)
    domain = r.netloc
    if r.query:
        query = r.query.split('=')[-1]
        return url, domain, query
    else:
        if r.path and r.path.endswith('.html'):
            # example.com/archive/432523.html
            path = r.path.split('/')[-1].split('.')[0]
            return url, domain, path
        else:
            # example.com/<％エンコードされてる場合>
            path = unquote(r.path.strip('/'))
            return url, domain, path


def add_parsing_link(url):
    parsed_list = []
    for u in url:
        parsed_url = _to_parse(u)
        parsed_list.append(parsed_url)
    return parsed_list


def to_create_image_links(url):
    response = fetch_link(url)
    links = [
        link for link in response.html.absolute_links
        if link.endswith(file_ext)
        ]
    links = list(map(trim_escape_text, links))
    if links:
        return links, fetch_article_title(response)
    return False


def to_create_save_directory(save_path):
    if not save_path.exists():
        save_path.mkdir(parents=True)
        return True
    return False


def to_create_path(domain, params):
    path = save_path / domain / params
    return path


def save_image(img_file, save_path):
    try:
        filename = img_file.url.split('/')[-1]
    except AttributeError:
        pass
    img_path = save_path / filename
    with open(img_path, 'wb') as _f:
        _f.write(img_file.content)


def trim_escape_text(link):
    splited_link = link.split('\\/')
    if len(splited_link) > 1:
        return "".join(splited_link)
    return splited_link[0]


def is_existing_files(links, save_path):
    def _search_fulllink(diff_files, links):
        return [link for df in diff_files for link in links if df in link]

    new_files = set(map(lambda x: x.split('/')[-1], links))
    files = set(map(lambda x: x.name, save_path.glob('*')))
    # 左辺の要素が全て右辺に含まれるならばTrue
    if not new_files <= files:
      # 左辺のみに含まれる要素を代入
      diff_files = new_files - files
      return _search_fulllink(diff_files, links)
    return False


def put_message(msg):
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()


def fetch_message(i, link, links):
    msg = f'{i}/{str(len(links))} Now Downloading.. {link}'
    put_message(msg)


def fetch_error_message(link):
    msg = f'-> Could not download image {link}'
    put_message(msg)


def get_argv():
    return sys.argv[0], sys.argv[-1]


def retry_message():
    py_file, url = get_argv()
    put_message('Please retry')
    put_message(f'python {py_file} {url}')


def uncompleted_links_message(incomplete_link):
    if incomplete_link:
        msg = 'Download uncompleted'
        put_message(msg)
        msg = "\n".join(incomplete_link)
        put_message(msg)

        retry_message()


def fetch_article_title(response):
    return response.html.find('title', first=True).text


def do_download_links(links, save_path):
    incomplete_link = []
    for i, link in enumerate(links, start=1):
        try:
            img = fetch_link(link)
        except:
            fetch_error_message(link)
            incomplete_link.append(link)
            continue

        if img:
            save_image(img, save_path)
        else:
            incomplete_link.append(link)

        fetch_message(i, link, links)
        sleep(INTERVAL_SLEEP)
    else:
        uncompleted_links_message(incomplete_link)


def main():
    parser = ArgumentParser()
    parser.add_argument('arg', nargs='+', type=str) #list
    args = parser.parse_args()

    if args.arg:
        for url, domain, params in add_parsing_link(args.arg):
            links, article_title = to_create_image_links(url)

            if use_directoryname_title:
                save_path = to_create_path(domain, article_title)
            else:
                save_path = to_create_path(domain, params)

            if not to_create_save_directory(save_path):
                # save_pathが存在しなければ、新規作成し、linksをダウンロード
                # 既存ならば、不足分をチェックし、不足分のリストを返す。
                links = is_existing_files(links, save_path) # Falseならば

            if links:
                put_message(article_title)
                do_download_links(links, save_path)


if __name__ == "__main__":
    main()

