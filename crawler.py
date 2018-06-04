# -*- coding: utf-8 -*-
# Python 3 версии
import os
import requests
import shutil
from bs4 import BeautifulSoup
import cssutils
import logging
import urllib3
import time
from threading import Thread
import database
import re
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
cssutils.log.setLevel(logging.CRITICAL)

class Crawler(Thread):
    not_allowed_links = ['.pdf', '.doc', '.docx', '.djvu', '.xml']
    storage_path = '/storage/'
    page_request = "page"
    asset_request = "asset"
    alowed_img_exts = ['.png', '.jpg', '.ico', '.svg']

    def __init__(self, url, project_name, user_id, project_id):
        Thread.__init__(self)
        self.storage_path = self.storage_path + user_id + '/'
        self.project_id = project_id
        self.url = url if url.endswith('/') else url + '/'
        self.project_name = project_name
        self.visited_links = []
        self.visited_assets = []
        self.error_links = []
        self.error_files = []
        self.slash_count = self.url.count('/')
        self.start_time = time.time()
        self.end_time = ""
        self.mysql = database.MySql()

    def do_request(self, link, stream=False, type=page_request):
        try:
            r = requests.get(link, stream=stream, verify=False)
            if type == self.page_request:
                self.visited_links.append(link)
            elif type == self.asset_request:
                self.visited_assets.append(link)
            return r
        except requests.exceptions.ConnectionError as e:
            self.error_links.append(link)
            print("Error on request. Error number: " + e.errno)

    def get_requestable_link(self, link):
        if "http://" not in link and "https://" not in link:
            link = self.url + link

        return link

    def get_all_links(self, text):
        soup = self.get_soup(text)
        return soup.find_all('a')

    def get_project_path(self):
        project_path = self.storage_path + self.project_name

        if not project_path.endswith('/'):
            project_path = project_path + '/'
        return project_path

    def get_dir(self, path, absolute=False):
        project_path = self.get_project_path()
        if path == '/':
            path = ''

        if not project_path.endswith('/') and not path.startswith('/'):
            path = '/' + path

        if not project_path.endswith('/') and not path.startswith('/'):
            path = '/' + path

        full_path = project_path + path
        if absolute == True:
            os.makedirs(full_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    def get_soup(self, text):
        return BeautifulSoup(text, 'html.parser')

    def save_img(self, text):
        soup = self.get_soup(text)
        links = soup.find_all("img")
        for l in links:
            href = l.get("src")
            if href is not None and href not in self.visited_links:
                if "//" in href:
                    path_s = href.split("/")
                    file_name = ""
                    for i in range(self.slash_count, len(path_s)):
                        file_name = file_name + "/" + path_s[i]
                else:
                    file_name = href

                link = self.get_requestable_link(file_name)

                if link in self.visited_assets:
                    continue

                r = self.do_request(link, stream=True, type=self.asset_request)

                if r.status_code == 200:
                    file_name = file_name.split("?")[0]
                    full_path = self.get_dir(file_name)

                    with open(full_path, "wb") as f:
                        shutil.copyfileobj(r.raw, f)

    def save_untaged_img(self, text):
        links = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', text)
        for l in links:
            href = str(l)
            
            if not any((href.endswith(ext) for ext in self.alowed_img_exts)):
                continue

            
            if href is not None and href not in self.visited_links:
                if "//" in href:
                    path_s = href.split("/")
                    file_name = ""
                    for i in range(self.slash_count, len(path_s)):
                        file_name = file_name + "/" + path_s[i]
                else:
                    file_name = href

                link = self.get_requestable_link(file_name)

                if link in self.visited_assets:
                    continue

                r = self.do_request(link, stream=True, type=self.asset_request)

                if r.status_code == 200:
                    file_name = file_name.split("?")[0]
                    full_path = self.get_dir(file_name)

                    with open(full_path, "wb") as f:
                        shutil.copyfileobj(r.raw, f)

    def save_assets(self, text, element, check):
        soup = self.get_soup(text)
        assets = soup.find_all(element)

        for link in assets:
            if element == "link":
                href = link.get("href")
            else:
                href = link.get("src")
            if href is not None and href not in self.visited_links:
                if check in href:
                    if "//" in href:
                        path_s = href.split("/")
                        file_name = ""
                        for i in range(self.slash_count, len(path_s)):
                            file_name = file_name + "/" + path_s[i]
                    else:
                        file_name = href

                    l = self.get_requestable_link(file_name)

                    if l in self.visited_assets:
                        continue

                    r = self.do_request(l, type=self.asset_request)

                    if r.status_code == 200:
                        file = file_name.split("?")[0]
                        full_path = self.get_dir(file)

                        with open(full_path, "wb") as f:
                            if element == "link" and check == ".css":
                                text = r.text.replace('//', 'http://')
                            else:
                                text = r.text

                            f.write(text.encode('utf-8'))
                            f.close()

                        if element == "link":
                            self.save_css_assets(full_path)

    def save_css_assets(self, path):
        project_path = self.get_project_path()
        file_name = path.replace(project_path, '')
        try:
            css = cssutils.parseFile(path)
            urls = cssutils.getUrls(css)
        except:
            self.error_files.append(file_name)
            return
        file_path = file_name.rsplit('/', 1)[0] 
        for url in urls:
            if 'http' not in url and 'https' not in url:
                url = url.rsplit('/', 1)
                if len(url) == 1:
                    asset = '/' + url[0]
                    path = ''
                elif len(url) > 1:
                    asset = '/' + url[1]
                    path = '/' + url[0]
                else:
                    continue
                if "../" in path:
                    path_a = path.split("../")
                    if path_a[-1] != '':
                        sub_path = file_path.split('/')
                        for i in range(len(path_a) - 1):
                            sub_path = sub_path[:-1]
                            path = '/' + path_a[-1]
                        sub_path = '/'.join(sub_path)
                else:
                    sub_path = file_path

                if sub_path.startswith('/'):
                    sub_path = sub_path[1:]

                l = self.get_requestable_link(sub_path + path + asset)

                if l in self.visited_assets:
                    continue

                r = self.do_request(l, stream=True, type=self.asset_request)

                if r.status_code == 200:
                    file = asset.split('?')[0]
                    full_path = self.get_dir(sub_path + path,True)

                    if file.endswith('.css'):
                        with open(full_path + file, "wb") as f:
                            f.write(r.text.encode('utf-8'))
                            f.close()
                        self.save_css_assets(full_path + file)
                    else:
                        with open(full_path + file, "wb") as f:
                            shutil.copyfileobj(r.raw, f)

    def parse(self, link):
        path_s = link.split("/")
        file_name = ""
        for i in range(self.slash_count, len(path_s)):
            file_name = file_name + "/" + path_s[i]

        if file_name[len(file_name) - 1] != "/":
            file_name = file_name + "/"

        file_name = file_name.split("?")[0]
        link = self.get_requestable_link(link)
        r = self.do_request(link)

        if r.status_code == 200:
            full_path = self.get_dir(file_name)

            with open(full_path + "index.html", "wb") as f:
                text = r.text.replace("href=\"" + self.url, "href=\"./")
                text = text.replace("href='" + self.url, "href='./")
                text = text.replace("src=\"" + self.url, "src=\"./")
                text = text.replace("src='" + self.url, "src='./")
                text = text.replace('src="/', 'src="./')
                text = text.replace('href="/', 'href="./')
                f.write(text.encode(r.encoding))
                f.close()

            self.save_img(r.text)
            self.save_untaged_img(r.text)
            self.save_assets(r.text, element="link", check=".css")
            self.save_assets(r.text, element="script", check=".js")

            links = self.get_all_links(r.text)


            try:
                for link in links:
                    href = link.get("href")
                    href = self.get_requestable_link(href)
                    exec_time = time.time() - self.start_time

                    if exec_time > 3*60:
                        break

                    if not href.startswith(self.url):
                        continue

                    try:
                        if href in self.visited_links or href in self.error_links:
                            continue

                        if not any((href.endswith(ext) for ext in self.not_allowed_links)):
                            self.parse(href)
                    except:
                        self.error_links.append(href)
            except:
                pass

    def setProjectPath(self):
        path = self.storage_path + self.project_name + ".zip"
        self.mysql.setItemDone(path, self.project_id)

    def makeArchive(self):
        zippath = self.get_project_path()
        shutil.make_archive(zippath, 'zip', self.storage_path, self.project_name)

    def run(self):
        print('started')
        self.parse(self.url)
        print('ended')
        self.makeArchive()
        self.setProjectPath()
        self.end_time = time.time()


        







