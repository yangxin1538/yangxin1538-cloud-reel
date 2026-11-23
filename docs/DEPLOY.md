# CloudReel 部署：所有 NAS 和云服务器

CloudReel 不认某个牌子的 NAS。只要能跑 Docker，就能装；两种装法都支持：`docker run` 和 `docker compose`。默认只占一个端口 **8088**。

## 两种装法

### A. Docker Compose（推荐）

```bash
git clone https://github.com/yangxin1538/yangxin1538-cloud-reel.git
cd yangxin1538-cloud-reel
cp .env.example .env   # 改里面的路径和 123 凭证
docker compose up -d
```

打开 `http://<你的主机>:8088`。

通用 `docker-compose.yml` 里所有主机路径都是变量，默认是相对路径（`./data`、`./config`、`./strm`、`./CloudNAS`），在 `.env` 里改成你的实际路径即可。没有本地挂载的云服务器，把 `CLOUDNAS_DIR` 留空或删掉那行挂载，123 / 光鸭直链不需要挂载。

### B. Docker Run

```bash
git clone https://github.com/yangxin1538/yangxin1538-cloud-reel.git
cd yangxin1538-cloud-reel
DATA_DIR=/data/cloud-reel/data STRM_DIR=/data/strm \
  CLOUDNAS_DIR=/mnt/CloudNAS sh deploy/docker-run.sh
```

云服务器没有本地挂载：`CLOUDNAS_DIR="" sh deploy/docker-run.sh`，只挂 `data` / `config` / `strm`。

也可以直接手写一条 `docker run`（等价于脚本做的事）：

```bash
docker build -t cloud-reel:latest .
docker run -d --name cloud-reel --restart unless-stopped \
  -p 8088:8088 \
  -e PUID=1000 -e PGID=1000 \
  -e SOURCE_ROOT=/CloudNAS -e STRM_ROOT=/strm/CloudReel \
  -v ./data:/app/data -v ./config:/app/config \
  -v ./strm:/strm -v ./CloudNAS:/CloudNAS:ro \
  cloud-reel:latest
```

## 各平台对照

| 平台 | 怎么装 | 路径怎么填 |
|---|---|---|
| Synology 群晖 | Container Manager → 项目 → 用 `docker-compose.yml`，或 `docker-compose.synology.yml`（已填好 `/volume1/...` 示例） | `DATA_DIR=/volume1/docker/cloud-reel/data`，`CLOUDNAS_DIR=/volume1/docker/clouddrive2/CloudNAS`，`STRM_DIR=/volume2/存储盘2/strm/media` |
| QNAP 威联通 | Container Station → 创建 → 用 `docker-compose.yml` | 填你的共享文件夹路径，如 `/share/CACHEDEV1_DATA/docker/cloud-reel/data` |
| UGREEN 绿联 | Docker → Compose 项目 → 粘贴 `docker-compose.yml` | 填你的存储路径，如 `/volume1/docker/cloud-reel/data` |
| TrueNAS / Unraid | Apps / Docker → 自定义应用 → 用 `docker-compose.yml` 或 `docker run` | 填你的数据集 / 共享路径 |
| Linux 云服务器 / VPS | `docker compose up -d` 或 `deploy/docker-run.sh` | 用 `./data` 等相对路径，或 `/opt/cloud-reel/data`；无挂载时 `CLOUDNAS_DIR=""` |
| Windows / macOS（Docker Desktop） | `docker compose up -d` | 相对路径即可，挂载用你共享给 Docker 的文件夹 |

关键点都一样：`data` / `config` 持久化，`strm` 输出目录要和 Emby 扫同一个目录，`CloudNAS` 是 CloudDrive2 挂载（有就挂，没有就不用）。

## 网络模式

默认是桥接（`ports: 8088:8088`），在哪都能用。以下情况再改 host 模式：

- CloudDrive2 挂载需要 `rslave` 传播，或
- Emby 和 CloudReel 在同一台机器、且要求容器内外路径完全一致。

改法：`docker-compose.yml` 里取消 `network_mode: host` 的注释，并删掉 `ports:` 那块。`docker run` 则把 `-p 8088:8088` 换成 `--network host`。

## 123 网盘凭证（可选）

只在走 123 真 API 直链时需要，在 `.env` 里填（不要贴到聊天里）：

```env
PAN123_CLIENT_ID=
PAN123_CLIENT_SECRET=
```

不填也能用：会回落到 `base_url` / 本地文件。光鸭同理：源上配 `base_url` + Bearer `auth_token` 就走直链。

## 检查是否跑起来

```bash
curl http://localhost:8088/health
# {"ok":true,"version":"0.3.2"}
curl http://localhost:8088/api/drives/123/status
```

升级：`git pull && docker compose up -d --build`（`docker run` 则是重新 build 后 `docker rm -f cloud-reel` 再跑一次脚本）。
