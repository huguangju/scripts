# Zread Downloader

这是一个用于将 Zread (zread.ai) 上的私有或公开文档仓库批量下载为本地 Markdown 文件的工具。

## 功能特性

*   **自动化爬取**：自动分析仓库主页，提取所有文档链接。
*   **格式保留**：下载文档并保存为 Markdown 格式。
*   **私有支持**：支持加载 Cookie 以访问私有仓库。
*   **智能命名**：自动根据项目名称生成输出目录。

## 环境要求

需要 Python 3.9 或更高版本。

1.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```
2.  安装 Playwright 浏览器（crawl4ai 依赖）：
    ```bash
    playwright install
    ```

## 使用方法

### 1. 准备 Cookie (可选)

如果是下载私有仓库，请在浏览器中登录 Zread，复制 Cookie 字符串（从开发者工具 Network 选项卡获取请求头中的 Cookie），并保存到当前目录下的 `cookies.txt` 文件中。

### 2. 运行脚本

**基本用法：**

指定仓库 URL 即可。默认会将文档下载到 `output/<项目名>` 目录下。

```bash
python3 download.py https://zread.ai/user/repo
```

**指定输出目录：**

使用 `-o` 或 `--output` 参数自定义下载目录。

```bash
python3 download.py https://zread.ai/user/repo -o my_docs
```

**指定 Cookie 文件：**

如果 Cookie 文件不在默认的 `cookies.txt`，可以使用 `-c` 参数指定。

```bash
python3 download.py https://zread.ai/user/repo -c /path/to/cookies.txt
```

## 命令行参数

*   `repo_url`: (必选) Zread 仓库的完整 URL (例如: `https://zread.ai/user/repo`).
*   `-o, --output`: (可选) 下载文件的输出目录。如果不指定，默认为 `output/<repo_name>`.
*   `-c, --cookies`: (可选) Cookie 文件路径。默认为 `cookies.txt`.
*   `--selector`: (可选) 用于提取主内容的 CSS 选择器。默认为 `main`。
*   `--exclude`: (可选) 要从下载内容中排除的元素的 CSS 选择器，多个选择器用逗号分隔。默认为 `nav,footer,header,aside`。

### 内容过滤示例

如果下载的文档包含不需要的导航栏、页脚或侧边栏，可以使用 `--selector` 指定主内容区域，或者使用 `--exclude` 排除特定元素。

**示例：只下载 `article` 标签内的内容，并排除类名为 `.ad-banner` 的元素**

```bash
python3 download.py https://zread.ai/user/repo --selector "article" --exclude ".ad-banner"
```
