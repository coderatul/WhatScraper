import sys
import re
import os
import urllib.request
import urllib.parse
import threading
import signal
from datetime import datetime
import argparse
import json
from html import unescape

try:
    from googlesearch import search
except ImportError:
    print("[!] No module named \"google\" found")
    print("    Please Install it by using:")
    print("\n    python3 -m pip install google")
    exit()

# Global stop event for threads
stop_event = threading.Event()

# Signal handler for Ctrl+C
def signal_handler(sig, frame):
    print("\n[!] Received Ctrl+C, stopping threads and exiting...")
    stop_event.set()  # Signal threads to stop
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

GROUP_NAME_REGEX = re.compile(r'(og:title\" content=\")(.*?)(\")')
GROUP_IMAGE_REGEX = re.compile(r'(og:image\" content=\")(.*?)(\")')
lock = threading.Lock()

SAVE = "scrapped_%s.txt" % datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
availabledom = ["pastebin",
                "throwbin",
                "pastr",
                "pasteio",
                "paste2",
                "hastebin",
                "gist.github",
                "ghostbin",
                "ideone",
                "codepen",
                "pastefs",
                "snipplr",
                "slexy",
                "justpaste",
                "0bin",
                "cl1p.net",
                "dpaste.com",
                "dpaste.org",
                "heypasteit.com",
                "hpaste.org",
                "ideone.com",
                "kpaste.net",
                "paste.kde.org",
                "paste2.org",
                "pastebin.ca",
                "pastebin.com",
                "paste.org.ru",
                "pastie.org",
                "snipplr.com",
                "paste.org"]
site_urls = ["https://www.whatsapgrouplinks.com/",
             "https://whatsgrouplink.com/",
             "https://realgrouplinks.com/",
             "https://appgrouplink.com/",
             "https://whatsfunda.com/",
             "https://whatzgrouplink.com/latest-whatsapp-group-links/",
             "https://allinonetrickz.com/new-whatsapp-groups-invite-links/"]


def linkcheck(url):
    if stop_event.is_set():
        print("[DEBUG] linkcheck: Stop event set, exiting")
        return {"name": None, "url": url, "image": None}
    print("\nTrying URL:", url, end='\r')
    group_info = {"name": None, "url": url, "image": None}
    try:
        hdr = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        }
        req = urllib.request.Request(url, headers=hdr)
        resp = urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[DEBUG] linkcheck: Failed to fetch {url}: {e}")
        return group_info
    if resp.getcode() != 404:
        resp = resp.read().decode("utf-8")
        group_info["name"] = unescape(GROUP_NAME_REGEX.search(resp).group(2))
        group_info["image"] = unescape(GROUP_IMAGE_REGEX.search(resp).group(2))
    return group_info


def pad(s):
    if "invite" not in s:
        p = s.find(".com")
        s = s[:p + 4] + "/invite" + s[p + 4:]
    return s


def scrape(txt, download_image=False):
    if stop_event.is_set():
        print("[DEBUG] scrape: Stop event set, exiting")
        return
    if isinstance(txt, bytes):
        txt = txt.decode("utf-8")
    match = []
    match2 = re.findall(
        r"(https:\/\/chat\.whatsapp\.com\/(invite\/)?[a-zA-Z0-9]{22})", txt)
    match = [item[0] for item in match2]
    match = list(set(match))
    for lmt in match:
        if stop_event.is_set():
            print("[DEBUG] scrape: Stop event set in loop, breaking")
            break
        lmt = pad(lmt)
        info = linkcheck(lmt)
        if info['name']:
            print("[i] Group Name:  ", info['name'])
            print("[i] Group Link:  ", info['url'])
            print("[i] Group Image: ", info['image'])
            lock.acquire()
            try:
                if SAVE.endswith(".json"):
                    with open(SAVE, "r+", encoding='utf-8') as jsonFile:
                        data = json.load(jsonFile)
                        data.append(info)
                        jsonFile.seek(0)
                        json.dump(data, jsonFile)
                        jsonFile.truncate()
                else:
                    with open(SAVE, "a", encoding='utf-8') as f:
                        write_data = " | ".join(info.values()) + "\n"
                        f.write(write_data)
                if download_image:
                    image_path = urllib.parse.urlparse(info['image'])
                    path, _ = urllib.request.urlretrieve(
                        info["image"], os.path.basename(image_path.path), timeout=10)
                    print("[i] Image Path: ", path)
            finally:
                lock.release()


def scrap_from_google(index):
    print("[*] Initializing...")
    if index >= len(availabledom) or stop_event.is_set():
        print("[DEBUG] scrap_from_google: Stop event set or invalid index, exiting")
        return
    query = "intext:chat.whatsapp.com inurl:" + availabledom[index]
    print("[*] Querying Google By Dorks ...")
    try:
        for url in search(query, tld="com", num=5, stop=5, pause=1):
            if stop_event.is_set():
                print("[DEBUG] scrap_from_google: Stop event set in loop, breaking")
                break
            hdr = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/'
            }
            req = urllib.request.Request(url, headers=hdr)
            txt = urllib.request.urlopen(req, timeout=10).read().decode("utf8")
            scrape(txt)
    except Exception as e:
        print(f"[DEBUG] scrap_from_google: Error during search: {e}")


def scrap_from_link(index):
    print("[*] Initializing...")
    if index >= len(site_urls) or stop_event.is_set():
        print("[DEBUG] scrap_from_link: Stop event set or invalid index, exiting")
        return
    print(f"[DEBUG] scrap_from_link: Fetching {site_urls[index]}")
    try:
        hdr = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        }
        req = urllib.request.Request(site_urls[index], headers=hdr)
        r = urllib.request.urlopen(req, timeout=10).read().decode()
        scrape(r)
    except Exception as e:
        print(f"[DEBUG] scrap_from_link: Error fetching {site_urls[index]}: {e}")
        return  # Explicitly return to ensure thread exits


def update_tool():
    print("[*] Updating Please Wait...")
    try:
        txt = urllib.request.urlopen(
            "https://github.com/TheSpeedX/WhatScraper/raw/master/whatscraper.py", timeout=10).read()
        with open(sys.argv[0], "wb") as f:
            f.write(txt)
        print("[$] Update Successful")
        print("[i] Run " + sys.argv[0] + " Again..")
    except Exception:
        print("[!] Update Failed !!!")
    sys.exit(0)


def initialize_google_scrapper():
    threads = []
    size = len(availabledom)
    prompt = "[#] Enter the number of threads(1-" + str(size) + "):- "
    thread_count = min(size, int(input(prompt)) + 1)
    for i in range(thread_count):
        thread = threading.Thread(target=scrap_from_google, args=(i,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for i in threads:
        while i.is_alive() and not stop_event.is_set():
            i.join(timeout=1.0)  # Check stop_event periodically
        if stop_event.is_set():
            print("[DEBUG] initialize_google_scrapper: Stop event set, exiting join")
            break


def initialize_site_scrapper():
    threads = []
    size = len(site_urls)
    prompt = "[#] Enter the number of threads(1-" + str(size) + "):- "
    thread_count = min(size, int(input(prompt)))
    for i in range(thread_count):
        thread = threading.Thread(target=scrap_from_link, args=(i,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for i in threads:
        while i.is_alive() and not stop_event.is_set():
            i.join(timeout=1.0)  # Check stop_event periodically
        if stop_event.is_set():
            print("[DEBUG] initialize_site_scrapper: Stop event set, exiting join")
            break


def initialize_file_scrapper():
    threads = []
    path = input("[#] Enter Whatsapp Link File Path: ").strip()
    if not os.path.isfile(path):
        print("\t[!] No such file found...")
        exit()
    thn = int(input("[#] Enter the number of threads: "))
    op = open(path, "rb").read().decode("utf-8")
    op = op.count('\n') // thn
    with open(path, "r", encoding='utf-8') as strm:
        for _ in range(thn - 1):
            head = [next(strm) for x in range(op)]
            thread = threading.Thread(
                target=scrape, args=(b'\n'.join(head),))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        thread = threading.Thread(target=scrape, args=(strm.read(),))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for i in threads:
        while i.is_alive() and not stop_event.is_set():
            i.join(timeout=1.0)  # Check stop_event periodically
        if stop_event.is_set():
            print("[DEBUG] initialize_file_scrapper: Stop event set, exiting join")
            break


def main():
    global SAVE
    print("STARTING WhatScraper !!!")
    parser = argparse.ArgumentParser(description="Scrap Whatsapp Group Links")
    parser.add_argument("-j", "--json", action="store_true",
                        help="Returns a JSON file instead of a text")
    parser.add_argument("-l", "--link", action="store",
                        help="Shows Group Info from group link")
    parser.add_argument("-u", "--update", action="store_true",
                        help="Update WhatScrapper")
    args = parser.parse_args()
    if args.update:
        update_tool()
    if args.link:
        scrape(args.link, download_image=True)
        return
    if args.json:
        SAVE = SAVE.split(".")[0] + ".json"
        with open(SAVE, "w", encoding='utf-8') as jsonFile:
            json.dump([], jsonFile)
    print("""
    1> Scrape From Google
    2> Scrape From Group Sharing Sites [BEST]
    3> Check From File
    4> Update WhatScrapper
    """)

    try:
        inp = int(input("[#] Enter Choice: "))
    except ValueError:
        print("\t[!] Invalid Choice..")
        exit()

    try:
        if inp == 1:
            initialize_google_scrapper()
        elif inp == 2:
            initialize_site_scrapper()
        elif inp == 3:
            initialize_file_scrapper()
        elif inp == 4:
            update_tool()
        else:
            print("[!] Invalid Choice..")
    except KeyboardInterrupt:
        print("\n[!] Received Ctrl+C in main, stopping threads and exiting...")
        stop_event.set()
        sys.exit(0)


if __name__ == "__main__":
    main()