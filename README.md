# CloudReel

为 CloudDrive2（CD2）+ Emby / Jellyfin 打造的网盘 STRM 生成器。

视频本体留在网盘里，本地只留很小的 `.strm` 指针文件，Emby / Jellyfin 扫到就能播，不占本地硬盘。

> 这是按 MoviDock 的功能思路重新实现的干净版本，不含原项目代码。

## 数据流

```
CloudDrive2 挂载的网盘 (/CloudNAS)
  → CloudReel 扫描、识别电影 / 剧集
  → 生成 .strm 到 /strm/CloudReel
  → Emby / Jellyfin 扫描该目录、刮削、播放
```

`.strm` 只是一个文本指针，存的是视频地址，不是视频本身。

## 功能

### v0.2：NextEmby + NextFind 集成

灵感来自 [wiki.nextemby.com](https://wiki.nextemby.com)，按 CloudReel 的单端口思路重新实现，不含原项目代码：

- **多源注册（NextEmby 服务器配置）**：`GET/POST /api/sources`，源类型有 `clouddrive2`、`115`、`123`、`guangya`（光鸭）、`local`、`remote`，带权重和启用开关，默认源就是 CD2 的 `/CloudNAS`。

### v0.3：123 网盘 + 光鸭云盘

- **123 网盘**：源类型 `123`，分流模式 `direct123`。123 有开放平台，流程是 `RequestAccessToken(client_id, client_secret)` → `EnableDirectLink(fileId)` → `GetDirectLinkUrl(fileId)`。大文件（>100MB）通常要登录后的 Authorization，否则会报 5112 / 请登录后下载。CloudReel 里配 `base_url`（直链入口）和 `auth_token` 就能走 302，没配就走 CD2 / 本地挂载读文件。
- **光鸭云盘**：源类型 `guangya`（标识 `gy`，迅雷旗下），分流模式 `directguangya`。光鸭面向第三方应用开放直连，单文件直链是临时链接，需要登录后捕获的 Bearer Authorization，直链有时效。CloudReel 不编造官方接口，没配 `base_url` 时会明确报错，配了就走 302，没配就走 CD2 / 本地挂载。
- **分享链接识别**：`app/drives.py` 能识别 123 分享域名（`yun.123pan.com` / `www.123pan.com` / `*.share.123pan.cn`）。
- **安全**：`auth_token` 只存在本机的 `data/sources.json` 里，不进 git，列表接口会打码显示。
- **分流网关（NextEmby）**：四种模式 `smart` 智能分流、`designated` 指定网盘、`direct115` 115 直连、`redirect302` 302 跳转。`POST /api/resolve` 试算，`GET /play?path=...&user=...` 按用户模式分流，直链 302，本地文件直接 serving。
- **Emby 反向代理**：`GET /emby/*` 透传到 `EMBY_UPSTREAM`（如 `http://127.0.0.1:8096`）。CloudReel 只用 8088 一个端口，不像 NextEmby 那样占 8091/8097/8098 三个端口。
- **直链缓存**：解析结果按 `CACHE_TTL_SECONDS`（默认 3600 秒）缓存，`GET /api/cache` 查看，`POST /api/cache/clear` 清空。
- **用户管理**：`GET/POST /api/users`，绑定 Emby 用户、按用户定分流模式和指定源，默认有 `admin` 用户。
- **播放与操作日志**：`GET /api/logs`，记录扫描、播放、分流失败，最多保留 500 条。
- **发现与缺集诊断（NextFind）**：`POST /api/discovery/ingest` 粘贴频道 / 分享链接文本导入，`POST /api/discovery/diagnose` 对比 STRM 库报缺集，只用路径模式 STRM，和 NextFind v3.7.7 的做法一致。Telegram 频道自动订阅需要 Bot Token，本版先做手动导入，接口留好了。
- **插件系统**：`plugins/*.py` 里放 `PLUGIN` 字典和 `run()`，`GET /api/plugins` 列出，`POST /api/plugins/{name}/run` 运行。已带一个 `pansou` 示例插件（未接真实接口，不会返回假链接）。

### v0.1

- 扫描 CD2 挂载目录，支持电影和剧集
- 文件名解析：`电影名 (2024).mkv`、`剧名.S01E01.mkv` 等
- 生成规范目录结构：
  - 电影：`Movies/电影名 (2024)/电影名 (2024).strm`
  - 剧集：`TV/剧名/Season 01/剧名 - S01E01.strm`
- 增量扫描：只处理新增 / 变化的文件
- 同步清理：源文件删除、改名、移动后，对应的 `.strm` 会被清理或更新
- 两种 STRM 模式：
  - `file`（默认，适合 CD2 本地挂载）：`.strm` 里写源文件的绝对路径，Emby 能直接读到同一挂载
  - `url`：`.strm` 里写 `STRM_BASE_URL + 相对路径`，适合走 302 直链 / WebDAV 的场景
- Web 管理端：改配置、手动触发扫描、看状态和日志
- 定时扫描：按 `SCAN_INTERVAL_MINUTES` 自动跑

## 快速开始（群晖 / Synology）

前提：CloudDrive2 已在群晖上把网盘挂到 `/volume1/docker/clouddrive2/CloudNAS`，
Emby 已装好。

1. 在群晖上创建目录：
   - `/volume1/docker/cloud-reel/data`
   - `/volume1/docker/cloud-reel/config`
   - `/volume2/存储盘2/strm/media/CloudReel`

2. 用 `docker-compose.synology.yml` 部署（见该文件，路径按你的实际盘符改）：

```bash
docker compose -f docker-compose.synology.yml up -d
```

3. 打开 `http://群晖IP:8088`，确认源目录是 `/CloudNAS`、输出目录是 `/strm/CloudReel`，点「立即扫描」。

4. 在 Emby 里新建媒体库，类型选电影 / 电视剧，路径指向：
   - `/volume2/存储盘2/strm/media/CloudReel/Movies`
   - `/volume2/存储盘2/strm/media/CloudReel/TV`

   Emby 容器也要能读到这个路径；如果 Emby 和 CloudReel 在同一台群晖上，用同样的宿主机路径挂载即可。

## 本地开发

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 准备一个示例源目录
mkdir -p /tmp/cd2-demo/电影 /tmp/strm-demo
cp 你的测试视频 /tmp/cd2-demo/电影/示例电影\ \(2024\).mkv

SOURCE_ROOT=/tmp/cd2-demo STRM_ROOT=/tmp/strm-demo PORT=8088 \
  python -m app.main
```

打开 `http://127.0.0.1:8088`。

## 配置

环境变量优先于配置文件，配置文件在 `/app/config/config.json`（容器内路径）。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` | `8088` | Web 端口 |
| `SOURCE_ROOT` | `/CloudNAS` | CD2 挂载的网盘根目录 |
| `STRM_ROOT` | `/strm/CloudReel` | `.strm` 输出根目录 |
| `STRM_MODE` | `file` | `file` 或 `url` |
| `STRM_BASE_URL` | `` | `url` 模式下的前缀，如 `http://群晖IP:8088/proxy` 或你的 302 入口 |
| `SCAN_INTERVAL_MINUTES` | `60` | 定时扫描间隔，`0` 表示关闭 |
| `DATA_DIR` | `/app/data` | 状态文件目录 |
| `CONFIG_DIR` | `/app/config` | 配置文件目录 |
| `PUID` / `PGID` | `0` | 仅 Docker 入口使用，用于改输出目录属主 |

支持的视频扩展名：`.mkv .mp4 .avi .mov .wmv .flv .ts .m2ts .webm .rmvb`，
忽略 `sample`、`trailer` 等样片文件。

## 目录结构

```
.
├── app/
│   ├── main.py       # FastAPI 入口、Web API、定时扫描、分流/网关/发现
│   ├── config.py     # 配置加载（环境变量 + config.json）
│   ├── parser.py     # 文件名解析：电影 / 剧集
│   ├── scanner.py    # 扫描、生成、清理
│   ├── sources.py    # 多源注册
│   ├── drives.py     # 123 / 光鸭直链
│   ├── diversion.py  # 分流模式解析
│   ├── cache.py      # 直链缓存
│   ├── users.py      # 用户管理
│   ├── logs.py       # 操作/播放日志
│   ├── discovery.py  # 发现导入与缺集诊断
│   ├── gateway.py    # Emby 反向代理
│   ├── plugins.py    # 插件加载
│   └── __init__.py
├── plugins/
│   └── pansou.py     # 示例插件
├── web/
│   └── index.html    # 管理端页面
├── tests/
│   └── test_parser.py
├── Dockerfile
├── docker-compose.yml
├── docker-compose.synology.yml
└── requirements.txt
```

## 安全提醒

- 默认用 `network_mode: host` + root 运行，和你原来 MoviDock 的部署一致，方便写文件，但不要把它暴露到公网。
- `STRM_BASE_URL` 不要填带账号密码的直链。
- 升级前备份 `/volume1/docker/cloud-reel/data` 和 `config`。
