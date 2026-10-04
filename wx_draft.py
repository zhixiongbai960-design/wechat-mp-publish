#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送 HTML 文章到微信公众号草稿箱（带 IP 漂移重试）

用法：
  python3 wx_draft.py --title "标题" --content 正文.html --cover cover.png
                      [--author 志雄] [--digest 摘要] [--source-url ""]

凭据：从 ~/.workbuddy/wx_mp.env 读取（WX_APPID / WX_SECRET），也可由环境变量覆盖。
      该文件权限应为 600，内容禁止写入 skill、日志或提交到任何仓库。

流程：
  1. 取 access_token（40164 = IP 未加白名单，自动重试并打印本次出口 IP）
  2. 上传封面图为永久素材 -> thumb_media_id（草稿接口强制要求封面）
  3. draft/add 建草稿，并回读 draft/get 校验内容是否被微信过滤

坑位提示见 SKILL.md。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import uuid

ENV_FILE = os.path.expanduser("~/.workbuddy/wx_mp.env")
API = "https://api.weixin.qq.com"
MAX_RETRY = 30
RETRY_SLEEP = 0.3
_seen_ips = []


def load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 强制直连不走代理


def _get(url):
    return json.loads(OPENER.open(urllib.request.Request(url), timeout=30).read())


def _post(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json; charset=utf-8"},
                                 method="POST")
    return json.loads(OPENER.open(req, timeout=60).read())


def _post_file(url, filepath, field="media", mime="image/png"):
    boundary = uuid.uuid4().hex
    with open(filepath, "rb") as f:
        filedata = f.read()
    body = [
        ("--%s\r\n" % boundary).encode(),
        ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
         % (field, os.path.basename(filepath))).encode(),
        ("Content-Type: %s\r\n\r\n" % mime).encode(),
        filedata,
        ("\r\n--%s--\r\n" % boundary).encode(),
    ]
    req = urllib.request.Request(url, data=b"".join(body),
                                 headers={"Content-Type":
                                          "multipart/form-data; boundary=%s" % boundary},
                                 method="POST")
    return json.loads(OPENER.open(req, timeout=120).read())


def explain(err):
    tips = {
        40013: "AppID 不正确。",
        40001: "AppSecret 错误或已失效。",
        40125: "AppSecret 不正确。",
        40164: "出口 IP 未加白名单（改后需等 5-10 分钟生效）。",
        48001: "该公众号没有接口权限（草稿箱/素材管理需认证服务号或认证订阅号）。",
        45009: "接口调用超过限额。",
    }
    return tips.get(err.get("errcode"), err.get("errmsg", ""))


def get_token(appid, secret):
    url = ("%s/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s"
           % (API, appid, secret))
    for i in range(1, MAX_RETRY + 1):
        try:
            r = _get(url)
        except Exception as e:
            print("[token] 第 %d 次网络异常：%s" % (i, e)); time.sleep(RETRY_SLEEP); continue
        if "access_token" in r:
            print("[token] 第 %d 次成功 ✅" % i); return r["access_token"]
        if r.get("errcode") == 40164:
            m = re.search(r"invalid ip ([0-9.]+)", r.get("errmsg", ""))
            ip = m.group(1) if m else "?"
            if ip not in _seen_ips:
                _seen_ips.append(ip)
            if i <= 3:
                print("[token] 第 %d 次被拒，本次出口 IP=%s，重试…" % (i, ip))
            time.sleep(RETRY_SLEEP); continue
        print("[token] 失败 %s → %s" % (r.get("errcode"), explain(r))); sys.exit(1)
    print("[token] 重试 %d 次未命中白名单。遇到的 IP：%s" % (MAX_RETRY, ", ".join(_seen_ips)))
    sys.exit(1)


def read_body(path):
    """抽取正文：优先取带版式的根 section，退回整个 body 内容"""
    raw = open(path, encoding="utf-8").read()
    i = raw.find('<section style="color: rgb(55, 65, 81)')
    if i >= 0:
        j = raw.rfind("</section>") + len("</section>")
        return raw[i:j]
    i, j = raw.find("<body"), raw.rfind("</body>")
    if i >= 0 and j > i:
        b = raw[i + 6:j]
        b = re.sub(r"^\s*<[^>]+>", "", b, count=1)
        return b
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--content", required=True, help="正文 HTML 路径")
    ap.add_argument("--cover", required=True, help="封面图路径 png/jpg")
    ap.add_argument("--author", default="志雄")
    ap.add_argument("--digest", default="")
    ap.add_argument("--source-url", default="")
    args = ap.parse_args()

    load_env()
    appid = os.environ.get("WX_APPID", "").strip()
    secret = os.environ.get("WX_SECRET", "").strip()
    if not appid or not secret:
        print("缺凭据，请在 %s 填 WX_APPID / WX_SECRET" % ENV_FILE); sys.exit(1)

    token = get_token(appid, secret)

    up = _post_file("%s/cgi-bin/material/add_material?access_token=%s&type=image"
                    % (API, token), args.cover)
    if "media_id" not in up:
        print("[素材上传] 失败：%s / %s" % (up, explain(up))); sys.exit(1)
    thumb = up["media_id"]
    print("[素材上传] OK")

    content = read_body(args.content)
    payload = {"articles": [{
        "title": args.title, "author": args.author, "digest": args.digest,
        "content": content, "content_source_url": args.source_url,
        "thumb_media_id": thumb, "need_open_comment": 1, "only_fans_can_comment": 0,
    }]}
    dr = _post("%s/cgi-bin/draft/add?access_token=%s" % (API, token), payload)
    if "media_id" not in dr:
        print("[草稿创建] 失败：%s / %s" % (dr, explain(dr))); sys.exit(1)
    mid = dr["media_id"]
    print("[草稿创建] OK ✅ media_id=%s" % mid)

    # 回读校验
    back = _post("%s/cgi-bin/draft/get?access_token=%s" % (API, token), {"media_id": mid})
    item = back.get("news_item", [{}])[0]
    c = item.get("content", "")
    print("\n[回读校验] 正文 %d 字符 | SVG %d | section %d | img %d | 封面 %s"
          % (len(c), c.count("<svg"), c.count("<section"), c.count("<img"),
             "已绑定 ✅" if item.get("thumb_media_id") else "❌"))
    print("=== 去公众号后台「草稿箱」查看后群发 ===")


if __name__ == "__main__":
    main()
