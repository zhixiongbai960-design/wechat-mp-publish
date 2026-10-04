#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查当前网络的出口 IP 是否已在微信公众号 IP 白名单里。

为什么比查 ipip.net 准：它直接用 AppSecret 调微信 token 接口，
40164 报错里带的 IP 就是微信服务器实际看到的请求源 IP，和真实调用完全一致。

用法：
  python3 check_ip.py

输出示例：
  ✅ 当前网络可以正常调用公众号 API（IP 已在白名单）
  ⚠️ 当前出口 IP = 171.83.xxx.xxx —— 未在白名单，需要去后台添加（改后等 5-10 分钟）

路径：~/.workbuddy/skills/wechat-mp-publish/check_ip.py
"""
import json
import os
import re
import sys
import urllib.request

ENV_FILE = os.path.expanduser("~/.workbuddy/wx_mp.env")
API = "https://api.weixin.qq.com"
# 若本机在多个 IP 间漂移，可多试几次取并集
PROBES = 3


def load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def main():
    load_env()
    appid = os.environ.get("WX_APPID", "").strip()
    secret = os.environ.get("WX_SECRET", "").strip()
    if not appid or not secret:
        print("缺少凭据：%s 里应有 WX_APPID / WX_SECRET" % ENV_FILE)
        sys.exit(1)

    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 直连，不走代理
    url = ("%s/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s"
           % (API, appid, secret))

    ok_ip = None
    blocked = []
    for _ in range(PROBES):
        try:
            r = json.loads(op.open(urllib.request.Request(url), timeout=30).read())
        except Exception as e:
            print("网络异常：%s" % e)
            sys.exit(1)
        if "access_token" in r:
            ok_ip = True
            break
        m = re.search(r"invalid ip ([0-9.]+)", r.get("errmsg", ""))
        if m and m.group(1) not in blocked:
            blocked.append(m.group(1))
        else:
            print("其他错误 errcode=%s errmsg=%s" % (r.get("errcode"), r.get("errmsg")))
            sys.exit(1)

    if ok_ip:
        print("✅ 当前网络可以正常调用公众号 API（IP 已在白名单），直接跑 wx_draft.py 即可。")
    else:
        print("⚠️ 当前网络出口 IP 未在公众号白名单：")
        for ip in blocked:
            print("     %s" % ip)
        print("→ 去 公众号后台 设置与开发→基本配置→IP白名单 加上上述 IP")
        print("→ 改动约 5-10 分钟生效，然后再跑一次 python3 check_ip.py 确认")


if __name__ == "__main__":
    main()
