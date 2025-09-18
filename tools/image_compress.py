import os
import re
import subprocess

md_image_reg = re.compile(r"!\[(?P<img_name>.*)\]\((?P<img_path>.*)\)")
support_img = [
    ".png",
    ".jpg",
    ".jpeg",
]

# 获取所有content/posts中存在index.md的目录。
def get_all_posts_dir() -> list[str]:
    ret = []
    posts_dir = "./content/posts/"
    
    dirs = os.walk(posts_dir)
    for dirpath, dirnames, filenames in dirs:
        if dirpath == posts_dir:
            continue

        if filenames.count("index.md") != 1:
            print(f"Skip directory: {dirpath} !!!")
            continue
        
        ret.append(dirpath)

    return ret

# 获取markdown文件中的所有图片路径，尝试替换为webp。
def patch_index_md_images(md_path: str) -> list[str]:
    print(f">>> Patching {md_path}")
    
    f = open(f"{md_path}/index.md", "r")
    text = f.read()
    f.close()
    
    edited = False
    
    ms = md_image_reg.finditer(text)
    for m in ms:
        md_image_name = m.group("img_name")
        md_img_path = m.group("img_path")
        if md_img_path.endswith(".webp"):
            continue
        
        print(f"  - Convert {md_img_path}: ", end="")
        if not md_img_path.startswith("./"):
            print("\t\t NOT LOCAL !!!")
            continue
        
        img_path = f"{md_path}/" + md_img_path.removeprefix("./")
        
        md_webp_path = ""
        for si in support_img:
            if md_img_path.endswith(si):
                md_webp_path = md_img_path.removesuffix(si) + ".webp"
                break
        if md_webp_path == "":
            print("\t\t NOT SUPPORT FORMAT !!!")
            continue
        
        webp_path = f"{md_path}/" + md_webp_path.removeprefix("./")
        
        if not os.path.exists(img_path):
            print("\t\t NOT EXIST !!!")
            continue
        
        # fix binary permission
        os.chmod("./cwebp", 0o755)
        # convert image to webp
        child = subprocess.Popen(["./cwebp", img_path, "-metadata", "none", "-o", webp_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        child.wait()
        if child.returncode != 0:
            print("\t\t FAILED !!!")
            
            print(child.stdout.read().decode())
            print(child.stderr.read().decode())
            continue
        
        print("\t\t success")
        
        # delete old image
        os.remove(img_path)
        
        # replace image path
        text = text.replace(
            f"![{md_image_name}]({md_img_path})",
            f"![{md_image_name}]({md_webp_path})"
        )
        
        edited = True
        
    if not edited:
        return
    
    # 有需要的时候再写入文件，避免中途出错导致文件损坏。
    f = open(f"{md_path}/index.md", "w")
    f.write(text)
    f.close()


if __name__ == "__main__":
    posts_dirs = get_all_posts_dir()
    for d in posts_dirs:
        patch_index_md_images(d)
