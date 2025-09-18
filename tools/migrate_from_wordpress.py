import os
import csv
import yaml
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json


def update_post_alias():
    f = open("./tools/_rank-math-redirections-2024-12-03_07-39-19.csv")
    redirects = {}
    for line in csv.reader(f):
        src = line[1]
        dst = line[3]

        if src.startswith("posts/"):
            post_id = int(src.removeprefix("posts/"))
            if dst.startswith("https://blog.xuegaogg.com/") and dst.endswith("/"):
                post_key = dst.removeprefix(
                    "https://blog.xuegaogg.com/").removesuffix("/")
                redirects[post_key] = post_id
            else:
                print(f"Invalid redirect: {src} -> {dst}")
                continue

    dirs = os.walk('./content/posts/')
    for dirpath, dirnames, filenames in dirs:
        if dirpath == './content/posts/':
            continue

        if filenames.count("index.md") != 1:
            print(f"Invalid directory: {dirpath}")
            continue

        post_key = dirpath.removeprefix('./content/posts/')
        post_id = redirects.get(post_key)
        if post_id is None:
            print(f"Post {post_key} not found in redirects")
            continue

        f = open(f"{dirpath}/index.md", "r")
        text = f.read()
        yaml_texts = text.split("---", maxsplit=2)
        if len(yaml_texts) < 3:
            print(f"Invalid YAML: {dirpath}")
            continue

        yaml_text = yaml_texts[1]
        metadata = yaml.load(yaml_text, Loader=yaml.FullLoader)

        metadata["aliases"] = [
            f"/posts/{post_id}",
            f"/archives/{post_id}",
            f"/{post_key}",
        ]
        yaml_texts[1] = "\n" + yaml.dump(metadata, allow_unicode=True)

        text = "---".join(yaml_texts)
        f = open(f"{dirpath}/index.md", "w")
        f.write(text)
        f.close()


# 将post名称修改为slug。
def rename_posts():
    f = open("./tools/_rank-math-redirections-2024-12-03_07-39-19.csv")
    redirects = {}
    for line in csv.reader(f):
        src = line[1]
        dst = line[3]

        if src.startswith("posts/"):
            post_id = int(src.removeprefix("posts/"))
            if dst.startswith("https://blog.xuegaogg.com/") and dst.endswith("/"):
                post_key = dst.removeprefix(
                    "https://blog.xuegaogg.com/").removesuffix("/")
                redirects[post_id] = post_key
            else:
                print(f"Invalid redirect: {src} -> {dst}")
                continue

    dirs = os.walk('./content/posts/')
    for dirpath, dirnames, filenames in dirs:
        if dirpath == './content/posts/':
            continue

        if filenames.count("index.md") != 1:
            print(f"Invalid directory: {dirpath}")
            continue

        post_id = int(dirpath.removeprefix('./content/posts/'))
        post_key = redirects.get(post_id)
        if post_key is None:
            print(f"Post {post_id} not found in redirects")
            continue

        # rename directory
        new_dirpath = f"./content/posts/{post_key}"
        os.rename(dirpath, new_dirpath)


def generate_tags_and_categories():
    f = open("./tools/wpposts.html")
    soup = BeautifulSoup(f, 'html.parser')

    m = {
        0: '所有分类',
        73: '云原生',
        28: '写代码',
        21: '建机房',
        18: '建模',
        12: '建站',
        60: '搞网络',
        51: '摄影',
        1: '未分类',
        34: '概论',
        45: '玩机',
        62: '闲聊',
    }
    ret = []

    # class="hidden"
    # class="post_title"
    # class="tags_input"
    # class="post_category"
    # class="rank-math-canonical-placeholder-value"

    es = soup.find_all("div", class_="hidden")
    for e in es:
        title = e.find("div", class_="post_title")
        if title is None:
            continue
        title = title.decode_contents()

        tag = e.find("div", class_="tags_input").decode_contents()
        category = e.find("div", class_="post_category").decode_contents()

        cs = []
        for k in category.split(","):
            cs.append(m[int(k)])

        ret.append({
            "title": title,
            "tags": str(tag).split(", "),
            "categories": cs,
        })

        # break

    print(json.dumps(ret, indent=4, ensure_ascii=False))


def patch_tags_categories():
    f = open("./tools/tags_categories.json")
    data = json.load(f)

    dirs = os.walk('./content/posts/')
    for dirpath, dirnames, filenames in dirs:
        if dirpath == './content/posts/':
            continue

        if filenames.count("index.md") != 1:
            print(f"Invalid directory: {dirpath}")
            continue

        post_key = dirpath.removeprefix('./content/posts/')
        post_key = post_key.removesuffix('/')

        for item in data:
            f = open(f"{dirpath}/index.md", "r")
            text = f.read()
            yaml_texts = text.split("---", maxsplit=2)
            if len(yaml_texts) < 3:
                print(f"Invalid YAML: {dirpath}")
                continue

            yaml_text = yaml_texts[1]
            metadata = yaml.load(yaml_text, Loader=yaml.FullLoader)

            if item["title"] == metadata["title"]:
                metadata["tags"] = item["tags"]
                metadata["categories"] = item["categories"]
                yaml_texts[1] = "\n" + yaml.dump(metadata, allow_unicode=True)

                text = "---".join(yaml_texts)
                f = open(f"{dirpath}/index.md", "w")
                f.write(text)
                f.close()


if __name__ == "__main__":
    patch_tags_categories()
