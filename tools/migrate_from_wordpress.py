import os
import csv
import yaml
import xml.etree.ElementTree as ET


f = open("./tools/_rank-math-redirections-2024-12-03_07-39-19.csv")
redirects = {}
for line in csv.reader(f):
    src = line[1]
    dst = line[3]
    
    if src.startswith("posts/"):
        post_id = int(src.removeprefix("posts/"))
        if dst.startswith("https://blog.xuegaogg.com/") and dst.endswith("/"):
            post_key = dst.removeprefix("https://blog.xuegaogg.com/").removesuffix("/")
            # print(f"Redirecting post {post_id} to {post_key}")
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
    yaml_texts = text.split("---")
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
    yaml_texts[1] = yaml.dump(metadata, allow_unicode=True)
    
    text = "---".join(yaml_texts)
    f = open(f"{dirpath}/index.md", "w")
    f.write(text)
    f.close()
    
    # print(f"Post {post_key} -> {post_id}")
    
    # aliases = [
    #     f"/posts/{post_id}",
    #     f"/archives/{post_id}",
    #     f"/{post_key}",
    # ]
    
    # post_id = int(dirpath.removeprefix('./content/posts/'))
    # post_key = redirects.get(post_id)
    # if post_key is None:
    #     print(f"Post {post_id} not found in redirects")
    #     continue
    
    # # rename directory
    # new_dirpath = f"./content/posts/{post_key}"
    # os.rename(dirpath, new_dirpath)
