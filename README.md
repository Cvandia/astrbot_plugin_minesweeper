<div align="center">

# astrbot_plugin_minesweeper

<a href="https://github.com/Cvandia/astrbot_plugin_minesweeper">
<img src="https://count.getloli.com/get/@astrbot_plugin_minesweeper?theme=booru-lewd"></a>

_⭐基于 AstrBot 的多人扫雷游戏插件，使用 uv 管理⭐_

<a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.12+-blue"></a>
<a href="https://qm.qq.com/q/SL6m4KdFe4">
    <img src="https://img.shields.io/badge/QQ-1141538825-yellow"></a>
<a href="https://github.com/Cvandia/astrbot_plugin_minesweeper/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue"></a>
<a href="https://docs.astrbot.app/">
    <img src="https://img.shields.io/badge/AstrBot-%3E%3D4.16%2C%3C5-red"></a>
<a href="https://docs.astral.sh/uv/">
  <img src="https://img.shields.io/badge/uv-managed-de5fe9" alt="uv-managed"></a>
<a href="https://github.com/Cvandia/astrbot_plugin_minesweeper/blob/main/.github/workflows/ruff-check.yml">
    <img src="https://github.com/Cvandia/astrbot_plugin_minesweeper/actions/workflows/ruff-check.yml/badge.svg?branch=main"></a>

**中文简体**

</div>

---

## 📝 介绍

**适用于 AstrBot 的多人协作扫雷小游戏。**
基于 [noneplugin/nonebot-plugin-minesweeper](https://github.com/noneplugin/nonebot-plugin-minesweeper) 改写，保留初级、中级、高级、自定义棋盘、批量挖开与标记及 18 套皮肤。群聊成员共享棋盘，私聊独立进行；使用统一消息组件适配各平台，支持图片棋盘、文本棋盘、空闲超时，以及通过 LLM 工具自然语言开局和结束游戏。

> [!WARNING]
> 需要 AstrBot `>=4.16,<5`。各平台的 @、唤醒前缀和图片能力以 AstrBot 配置为准；图片无法发送时可开启文本模式。游戏保存在内存中，插件重载或机器人重启会结束当前游戏。自然语言功能需要当前会话启用支持工具调用的模型，并允许使用插件工具。

## 📜 免责声明

> [!CAUTION]
> 本项目仅供**学习**和**研究**使用，使用者需自行承担使用插件的风险。作者不对插件的使用造成的任何损失或问题负责。请合理使用插件，**遵守相关法律法规。**
使用**本插件即表示您已阅读并同意遵守以上免责声明**。如果您不同意或无法遵守以上声明，请不要使用本插件。

---

## 💿 安装

<details>
<summary>安装</summary>

`AstrBot 管理面板` 安装

```text
插件管理 → 安装插件 → 从链接安装
https://github.com/Cvandia/astrbot_plugin_minesweeper
```

`源码` 安装

```text
将整个 astrbot_plugin_minesweeper 目录放入 AstrBot/data/plugins/
在 AstrBot 使用的 Python 环境安装 requirements.txt，然后重载插件
```

`pip` 安装运行依赖

```bash
python -m pip install -r data/plugins/astrbot_plugin_minesweeper/requirements.txt
```

`uv` 本地开发
```bash
uv sync --locked --group integration
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

`git clone` 安装

- 在 AstrBot 根目录运行
```bash
git clone https://github.com/Cvandia/astrbot_plugin_minesweeper data/plugins/astrbot_plugin_minesweeper
python -m pip install -r data/plugins/astrbot_plugin_minesweeper/requirements.txt
```

 </details>

 <details>
 <summary>注意</summary>

 推荐镜像站下载

 清华源```https://pypi.tuna.tsinghua.edu.cn/simple```

 阿里源```https://mirrors.aliyun.com/pypi/simple/```

 请使用 AstrBot 自身的 Python 环境安装依赖；`uv sync` 用于开发，不会自动安装插件到 AstrBot。AstrBot SDK 集成测试可在满足 SDK Python 版本要求的环境中执行 `uv sync --locked --group integration`；未安装 SDK 时该测试组会明确跳过。

</details>

## 🚀 使用

> [!note]
> 命令遵循 AstrBot 的唤醒设置。示例省略前缀；如果配置了 `/`，请发送 `/扫雷`、`/挖开 A1`。群聊每群一局、私聊每人一局，不同平台实例和机器人账号相互隔离。默认任意成员均可结束游戏，可通过配置限制为发起者或 AstrBot 管理员。

### 指令：

| 指令  |  需要@   | 范围  |    说明     | 权限  |
| :---: | :------: | :---: | :---------: | :---: |
| 扫雷 / minesweeper | 根据配置 | all | 开始 8×8、10 雷的初级游戏 | all |
| 扫雷初级 / 扫雷中级 / 扫雷高级 | 根据配置 | all | 分别为 8×8/10、16×16/40、16×30/99 | all |
| 扫雷 -r 12 -c 16 -n 30 -s ocean | 根据配置 | all | 自定义行、列、雷数与皮肤 | all |
| 挖开 / open / wk A1 B2 | 根据配置 | all | 批量挖开，首次挖开安全 | all |
| 标记 / mark / bj A1 B2 | 根据配置 | all | 标记或取消标记，已标记格须先取消再挖开 | all |
| 查看游戏 / 查看游戏盘 / 显示游戏 / 显示游戏盘 / 查看扫雷 | 根据配置 | all | 显示棋盘并刷新空闲时间 | all |
| 结束扫雷 / 结束游戏 / 结束 | 根据配置 | all | 结束当前游戏 | 根据配置 |
| 扫雷帮助 / 扫雷 --help | 根据配置 | all | 查看帮助 | all |
| 扫雷皮肤 | 根据配置 | all | 查看全部皮肤名称 | all |

启用支持工具调用的模型后，可直接对机器人说“来一局扫雷”“开始一局中级扫雷”“开一个 12 行 16 列、30 个雷、ocean 皮肤的扫雷”或“结束这局扫雷”。插件注册 `minesweeper_start` 和 `minesweeper_stop` 两个 LLM 工具，由模型根据用户意图选择调用；未说明难度时默认初级。工具会直接发送棋盘或实际处理结果，挖开和标记仍使用上表中的指令。

工具仅操作当前聊天，无法由模型指定其他会话或伪造用户身份。已有游戏时保留原局；结束操作遵守 `stop_owner_only`，权限不足或没有游戏时会如实提示。自然语言是否触发工具取决于模型、工具开关及唤醒设置；指令始终可用。

位置为字母+数字，例如 `A1`；字母表示行，数字表示列，不区分大小写。可用空格或中英文逗号分隔，每次最多操作 100 个位置；重复位置只处理一次，格式错误时整批不执行。越界或已挖开的格子会给出提示，其他合法位置继续处理。

参数支持 `-r/--row`（8~24）、`-c/--col`（8~30）、`-n/--num`（不少于 10 且小于总格数）、`-s/--skin`，也可使用 `--row=12`。挖开全部安全格或正确标记全部地雷即可获胜；踩雷即失败，并显示地雷和错误标记。空闲超时默认 300 秒，用时从首次挖开开始计算。

皮肤：`clone`、`colorsonly`、`hibbeler`、`icicle`、`mario`、`maviz`、`mine`、`narkomania`、`ocean`、`pacman`、`predator`、`scratch`、`symbol`、`unknown`、`vista`、`win98`、`winbw`、`winxp`。

## ⚙️ 配置

**在 AstrBot 插件管理 → 扫雷游戏 → 配置中修改，保存后重载插件使所有设置生效**

| 基础配置 | 类型  | 必填项 | 默认值 | 说明  |
| :------: | :---: | :----: | :----: | :---: |
| default_skin | string | 否 | winxp | 默认皮肤，可被命令参数覆盖 |
| game_timeout | int | 否 | 300 | 空闲超时秒数，最少 10 秒，每 5 秒回收并尝试通知 |
| max_games | int | 否 | 100 | 同时进行的游戏上限，最少 1 局 |
| text_mode | bool | 否 | false | 使用纯文本棋盘；图片生成或发送异常也会回退文本 |
| stop_owner_only | bool | 否 | false | 限制只有发起者或 AstrBot 管理员能结束游戏 |

**注：插件通过上述配置项管理，无独立 dashboard 页面。列出的平台使用统一消息接口，尚需在各自真实机器人环境验证。**


## 🌙 Todo
 - [x] AstrBot 标准插件结构与配置 Schema
 - [x] 三档难度、自定义棋盘、18 套皮肤
 - [x] 群聊协作、超时清理、文本棋盘
 - [x] LLM 工具自然语言开局和结束扫雷
 - [x] uv 锁文件、Ruff 和自动化测试
 - [ ] 各平台真实机器人环境联调

**喜欢记得点个star⭐**

## 💝 特别鸣谢

- [x] [AstrBot](https://github.com/AstrBotDevs/AstrBot): 本项目的聊天机器人框架。
- [x] [noneplugin/nonebot-plugin-minesweeper](https://github.com/noneplugin/nonebot-plugin-minesweeper): 原扫雷插件、游戏逻辑及皮肤资源。
- [x] [Cvandia/uv-project-template](https://github.com/Cvandia/uv-project-template): 项目模板与 README 格式。
- [x] [mzdluo123/MineSweeper](https://github.com/mzdluo123/MineSweeper) 与 [Minesweeper X](https://www.curtisbright.com/msx/): 原项目致谢的扫雷实现与资源来源。

## Contributer

<a href="https://github.com/Cvandia/astrbot_plugin_minesweeper/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Cvandia/astrbot_plugin_minesweeper&max=1000" alt="contributors" />
</a>

## 📚 更多帮助

**开发与排障**
1. 使用 `扫雷帮助` 查看命令；收不到图片时，在插件配置开启 `text_mode`。
2. 查看 [AstrBot 文档](https://docs.astrbot.app/)、[更新日志](changelog.md) 和 [来源及许可](NOTICE.md)。`LOGO.png` 为项目图标；发布 ZIP 同时包含 AstrBot 自动识别的 `logo.png` 同图副本。Linux 从源码安装时可执行 `cp LOGO.png logo.png` 让管理面板识别图标。
3. 游戏逻辑位于 `src/astrbot_plugin_minesweeper/`，根目录 `main.py` 为 AstrBot 入口，`tools.py` 定义自然语言 LLM 工具。默认开发测试不依赖启动机器人；集成测试使用真实 AstrBot SDK 的命令过滤器、工具执行器、消息结果和插件生命周期。
4. 发布前运行 `uv run --locked pytest`、Ruff 检查及 `uv build`。执行 `python scripts/package_plugin.py` 可生成完整插件 ZIP。PyPI 工作流需配置 `PYPI_API_TOKEN`；构建的 Python 包提供游戏内核，AstrBot 安装应使用完整源码目录或仓库。
