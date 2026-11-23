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
│   ├── main.py       # FastAPI 入口、Web API、定时扫描
│   ├── config.py     # 配置加载（环境变量 + config.json）
│   ├── parser.py     # 文件名解析：电影 / 剧集
│   ├── scanner.py    # 扫描、生成、清理
│   └── __init__.py
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
