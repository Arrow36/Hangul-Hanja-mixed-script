# Hangul → Hanja Converter | 국한문혼용 변환기 | 汉谚混写转换器

**Hangul-Hanja Mixed Script / 國漢文混用體 / 국한문혼용체**

将现代韩文自动转换为汉字与谚文混写的汉谚混写转换器。# Hangul-Hanja Mixed Script
Convert modern Korean Hangul text into Hangul–Hanja mixed script.
한글 문장을 국한문혼용체로 변환하는 웹 기반 변환기입니다.

将韩文转换为汉谚混写的本地网页应用，结合词源展示、逐词释义与同音词候选选择，让阅读和查词在同一页面完成。
A local web app for Hangul–Hanja mixed-script reading, with etymology, dictionary lookup, and homonym selection.

体验网站：https://kr.103367.xyz/

![汉谚混写网页界面](docs/images/web-interface.png)

## 功能

- **实时转换**：输入韩文后显示转换结果；初次打开时会加载可编辑的示例文本并自动转换。
- **三种阅读模式**：注音式上下对照、汉谚混写、原文。
- **词源显示**：切换查看词典记录的原始词源，包括汉字、拉丁字母及混合文字。
- **逐词查词与候选选择**：点击词语查看释义，对有歧义的词选择候选。
- **词典详情**：按词条数据展示词性、词汇等级、分类、发音、词义、译词、例句、短语、对话、关联词及多媒体链接，并提供完整原始 JSON。
- **阅读设置**：突出显示开关、显示／隐藏空格、复制结果。标点符号不触发词典查询。
- **桌面与手机布局**：桌面词典侧栏关闭后保留位置；手机端的顶部标题栏和底部状态栏固定在可视区域，中间内容独立滚动并兼容安全区域。
- **12 种界面语言**：简体中文、한국어、English、日本語、Français、Español、Русский、Tiếng Việt、Монгол、العربية、ไทย、Bahasa Indonesia。首次访问会按浏览器语言自动选择，并记住用户后续的手动选择；释义译文依词典实际收录情况显示。

## 转换原则

本项目辅助阅读，不将整段韩语翻译成中文。助词、词尾和无法可靠转换的部分保留韩文；同音词仍可能需要人工判断。

`origin_raw` 是词典中的原始词源，`replacement` 是经过转换规则验证的替换文本，两者用途不同。例如 `게임기` 的词源可以是 `game機`，但不能因此在默认混写模式中直接替换成 `game機`。词源模式用于展示这些原始资料。

转换和词典查询在本地服务中完成，不需要大语言模型 API。首次安装依赖、下载词典及访问在线音频或其他外部资源需要网络。

## 形态分析与词典来源

本项目使用 **[kiwipiepy](https://github.com/bab2min/kiwipiepy)**（Kiwi 韩语形态分析器的 Python 接口）分析韩文，识别词干、助词、词尾及词性，并提供词语在原文中的位置，供转换逻辑匹配和保留原文结构。

例如，处理 `경제는` 时，形态分析帮助识别 `경제` 与助词 `는`；再结合词典中的 `경제 → 經濟`，生成 `經濟는`。

- **kiwipiepy**：负责韩语分词与形态分析，接入代码位于 [`app/services/tokenizer.py`](app/services/tokenizer.py)。
- **韩国语基础词典**：提供汉字词源、同音词条、释义及例证等数据。
- **本项目的转换逻辑**：结合分析结果与词典候选，判断替换范围并生成混写文本，代码位于 [`app/services/converter.py`](app/services/converter.py)。

kiwipiepy 已列入 [`requirements.txt`](requirements.txt)，按下方步骤安装依赖即可。感谢 kiwipiepy / Kiwi 与韩国语基础词典为本项目提供基础工具和数据。

## 快速开始

技术栈：Python、FastAPI、SQLite、kiwipiepy，以及原生 HTML / CSS / JavaScript。以下步骤请从项目根目录执行；本地使用 Python 3.12 验证。

### 1. 获取源码并安装依赖

```powershell
git clone https://github.com/Arrow36/Hangul-Hanja-mixed-script.git
cd Hangul-Hanja-mixed-script
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS / Linux 激活虚拟环境时使用 `source .venv/bin/activate`。

### 2. 准备并导入词典

数据来源为韩国国立国语院的 [한국어기초사전（韩国语基础词典）](https://krdict.korean.go.kr/)。请从官方获取完整 JSON 下载包，保留 ZIP 格式，无需手工解压。

**当前导入器针对 2026-08-19 完整 JSON 快照进行严格校验。** 其他日期的数据可能因词条数量或结构变化而导入失败，需要先调整导入校验并验证兼容性。

```powershell
python scripts/inspect_dictionary.py "path/to/전체 내려받기_한국어기초사전_json_20260819.zip"
python scripts/import_dictionary.py "path/to/전체 내려받기_한국어기초사전_json_20260819.zip"
```

将示例路径替换为实际文件路径。导入后的数据库默认为项目根目录的 `hanja_dict.db`。当前快照的参考数量：56,555 个词条、76,833 个义项、657,975 条例证记录，以及 34,142 个含汉字词源的词条。例证记录包括短语、句子、对话等，并非全部是独立例句。

导入器逐个读取 ZIP 中的 JSON，保留原始词条数据，完成校验后替换数据库，并为原数据库创建备份。重新导入前请停止正在运行的服务。

词典 ZIP、生成的 SQLite 数据库及备份不包含在本仓库中。

### 3. 启动

```powershell
python run.py
```

打开 <http://127.0.0.1:8000/>。默认启动器绑定本机地址，并启用开发热重载。API 文档位于 <http://127.0.0.1:8000/docs>。

## API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/convert` | 转换文本并返回分段、位置和候选 |
| POST | `/api/select-candidate` | 验证候选并生成替换文本 |
| GET | `/api/lookup` | 按词形、词源或词条 ID 查词 |
| GET | `/api/entries/{entry_id}` | 获取词条详情，`include_raw=true` 返回原始数据 |
| GET | `/api/version` | 查看版本与数据信息 |
| GET | `/api/stats` | 查看词典统计 |
| GET | `/api/debug/tokenize` | 查看形态分析结果 |

转换请求示例：

```json
{
  "text": "대한민국의 경제는 빠르게 발전하였다.",
  "request_id": "example-1"
}
```

完整参数与响应格式以运行服务后的 `/docs` 为准。

## 开发与测试

先完成词典导入，再安装测试依赖并运行集成与回归测试：

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest tests.test_integration tests.test_regression_fixed
```

`tests/test_e2e_api.py` 用于运行中服务的 API 检查；`tests/test_browser_ui.py` 为可选浏览器测试，需要额外安装 Selenium，并按测试文件配置本地 Edge 驱动。仓库不提供驱动二进制文件。

```text
app/                     FastAPI、数据访问、转换逻辑与网页
  services/              形态分析、词典查询、转换及消歧
  static/                页面和分类翻译资源
scripts/                 词典检查、导入、分类资源生成及验证工具
tests/                   集成、回归、API 与浏览器测试
run.py                   本地开发启动入口
```

## 已知边界与贡献

词典覆盖率、形态分析和同音消歧都会影响结果；候选评分不代表语义判断必然正确。部分词条缺少某种语言的译文、发音或多媒体内容，展示以实际数据为准。

欢迎通过 Issue 提交问题。转换问题请附上韩文输入、实际结果、预期结果及数据版本；界面问题请附上界面语言、屏幕尺寸和复现步骤。

## 数据来源与许可

词典内容来自韩国国立国语院 한국어기초사전，相关内容与在线资源的使用、分发请遵循其原有条款。项目代码的许可证不会替代词典数据或第三方依赖的许可。

项目代码采用 [GNU GPL v3.0](LICENSE)（GPL-3.0-only）。

维护者：[@Arrow36](https://github.com/Arrow36)
