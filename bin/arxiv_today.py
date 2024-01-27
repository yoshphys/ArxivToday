#!/usr/bin/env python3

import os
import re
import html
import json
import requests
import urllib.request as libreq
from html.parser import HTMLParser
from datetime import datetime, timedelta

Categories = ["nucl-ex", "hep-ex", "nucl-th", "hep-th"]
MaxResults = 10
MaxTranslations = 20

# __________________________________________________


class MyHTMLParser(HTMLParser):
    tags = ["id", "published", "title", "name", "summary"]
    tag = ""
    eid = ""
    flag = dict()
    entry = dict()
    entries = dict()
    dodump = False

    def initialize(self):
        self.eid = ""
        self.tag = ""
        self.entry = dict()
        self.flag = dict()

    def handle_starttag(self, tag, attrs):
        if self.dodump:
            print("Encountered a start tag:", tag)
        self.flag[tag] = True
        if "entry" in self.flag.keys() and self.flag["entry"] and tag in self.tags:
            self.tag = tag
        else:
            self.tag = ""

    def handle_endtag(self, tag):
        if self.dodump:
            print("Encountered an end tag :", tag)
        if "entry" in self.flag.keys() and self.flag["entry"] and "entry" == tag:
            self.entries[self.eid] = self.entry.copy()
            self.initialize()
        else:
            pass
        self.flag[tag] = False

    def handle_data(self, data):
        if self.dodump:
            print("Encountered some data  :", data)
        if not ("entry" in self.flag.keys() and self.flag["entry"]):
            return

        if "id" == self.tag and self.flag[self.tag]:
            self.eid = data.split("/")[-1]
            self.entry["id"] = data
        elif "name" == self.tag and self.flag[self.tag]:
            # if "name" in self.entry.keys():
            #     self.entry["name"].append(html.unescape(data))
            # else:
            #     self.entry["name"] = [html.unescape(data)]
            if "name" in self.entry.keys():
                if len(self.entry["name"]) < 3:
                    self.entry["name"].append(html.unescape(data))
            else:
                self.entry["name"] = [html.unescape(data)]
        elif self.tag in self.tags and self.flag[self.tag]:
            self.entry[self.tag] = html.unescape(
                re.sub(r" {2,}", " ", data.replace("\n", " ").strip())
            )
        else:
            pass

    def get_list(self):
        return self.entries

    def do_dump(self, flag):
        self.dodump = flag


# __________________________________________________


def get_api_info(path):
    url = ""
    param = dict()
    with open(path, "r") as f:
        buff = json.load(f)
        url = buff["scheme"] + "://" + "/".join([buff["FQDN"], buff["path"]])
        param["auth_key"] = buff["auth_key"]
    return url, param


# __________________________________________________


def translate(url, params, text):
    params["text"] = text
    request = requests.post(url, data=params)
    result = request.json()
    return result["translations"][0]["text"]


# __________________________________________________

ArxivApiUrl = "http://export.arxiv.org/api"
ArxivApiOptions = f"start=0&max_results={MaxResults}&sortBy=submittedDate"
ArxivApiQueries = [f"cat:{icat}&{ArxivApiOptions}" for icat in Categories]

DeeplApiConfigPath = os.path.join(os.path.dirname(__file__), "..", "api", "deepl.json")


def main():
    deeplurl, params = get_api_info(DeeplApiConfigPath)
    params["target_lang"] = "JA"

    entries = dict()
    for iquery in ArxivApiQueries:
        parser = MyHTMLParser()
        parser.do_dump(False)
        iurl = "/".join([ArxivApiUrl, f"query?search_query={iquery}"])
        buff = ""
        with libreq.urlopen(iurl) as response:
            buff = response.read().decode("utf-8")
        parser.feed(buff)
        entries.update(parser.get_list())

    theday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()

    body = f"Papers submitted on {theday} UTC.\n\n"

    n = 0
    nc0 = 0
    nc = 0
    for key, entry in entries.items():
        updated = entry["published"].split("T")[0]
        if updated != theday:
            continue
        inc = len(entry["summary"])
        nc0 += inc
        body += 3 * "-" + "\n"
        body += "## " + entry["title"] + "\n"
        # body += "- published: " + entry["published"] + '\n'
        body += "- author: " + ", ".join(entry["name"]) + "\n"
        body += "- abstract: " + entry["summary"] + "\n"
        if n < MaxTranslations:
            nc += inc
            body += (
                "- transliation: "
                + translate(deeplurl, params, entry["summary"])
                + "\n"
            )
        body += "- link: " + entry["id"] + "\n"
        body += "\n\n"

        n += 1

    body += f"abstract character count: {nc0}\n"
    body += f"translated character count: {nc}"

    if 0 == n:
        print(f"No paper submitted on {theday} UTC.")
    else:
        print(body)


# __________________________________________________

main()
