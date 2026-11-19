# 看拼音写词语（Pinyin-Writing-Worksheet）

在 ARM64 开发板（NanoPi R3S）上以 Docker 常驻运行的 Web 应用：
输入词语 → 自动生成逐字拼音 + 空心田字格 → 在线预览并下载 A4/A5 PDF。

## 本地开发

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 把字体放进 fonts/（见 fonts/README.md）

python app.py            # 调试模式 http://127.0.0.1:8000
# 或
gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:8000 --timeout 60 --access-logfile - wsgi:app
```

## 测试

```bash
pytest -q
```

## Docker 部署

```bash
# 在 R3S 上直接构建（约 10–20 分钟）
docker compose up -d --build

# 或在 x86 开发机交叉构建后导出
docker buildx build --platform linux/arm64 -t kan-pinyin:1.0 --load .
docker save kan-pinyin:1.0 | gzip > kan-pinyin-1.0-arm64.tar.gz
# 传到 R3S 后
gunzip -c kan-pinyin-1.0-arm64.tar.gz | docker load
docker compose up -d
```

访问 `http://<R3S-IP>:8000`。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 输入页面 |
| GET | `/healthz` | 健康检查，返回 `{"status":"ok"}` |
| POST | `/api/parse` | 解析词语，返回词语、拼音与警告（供前端实时提示） |
| POST | `/api/pdf` | 生成 PDF，返回 `application/pdf` 二进制流 |

`POST /api/pdf` 请求体示例：

```json
{
  "words": "春天\n花朵|huā duǒ\n小桥",
  "paper": "A4",
  "grid_size": 16,
  "pinyin_font_size": 10,
  "show_header": true,
  "show_answer": false,
  "shuffle": false,
  "show_page_number": false
}
```