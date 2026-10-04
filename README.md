# wechat-mp-publish

公众号排版 + 推送草稿箱 WorkBuddy Skill。

把 Markdown/HTML 文章排成公众号可直接发布的内联样式 HTML，渲染 2.35:1 封面图，并推送到微信公众号草稿箱。排版规范基于真实公众号文章 1:1 复刻，已验证正文内的 SVG 图标在发布后不被微信过滤。

## 包含文件

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 排版规范、封面渲染命令、推送流程与 IP 白名单坑位说明 |
| `wx_draft.py` | 推送 HTML + 封面到草稿箱（自动取 token、上传素材、draft/add、回读校验） |
| `check_ip.py` | 自检当前出口 IP 是否在公众号 IP 白名单 |

## 前置条件

1. **认证服务号或认证订阅号**（草稿箱 / 素材管理接口需认证，个人未认证订阅号返回 48001）
2. 在公众号后台「设置与开发 → 基本配置」配置 **IP 白名单**（本机出口 IP；动态 NAT 需把 IP 段加全）
3. 安装 Python 3（仅用标准库，无需 pip 依赖）

## 配置凭据（必须，且绝不提交）

在 `~/.workbuddy/wx_mp.env`（权限 600）填写：

```
WX_APPID=你的appid
WX_SECRET=你的appsecret
```

脚本会自动读取该文件；也可用环境变量覆盖。`.gitignore` 已排除 `*.env`，请勿将真实凭据提交到仓库。

## 用法

1. 按 `SKILL.md` 规范排版文章 HTML，并准备好 `cover.png` 封面图
2. 推送前自检网络：`python3 check_ip.py`
3. 推送：`python3 wx_draft.py --title "标题" --content 正文.html --cover cover.png --author 志雄 --digest "摘要"`
4. 去公众号后台「草稿箱」查看，确认无误后群发（群发动作由人操作）

## 安全

- 凭据只存本地 env，禁止写入 skill / 日志 / 提交仓库
- AppSecret 属于敏感凭证，请勿公开分享或重置（重置会让旧凭据失效）

## 说明

本 skill 的署名 / 品牌字段（志雄、志亚科技等）为作者个人配置，他人 clone 后按需替换即可。
