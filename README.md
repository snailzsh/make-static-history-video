# make-static-history-video

面向 AI Agent 的中文竖屏静态历史信息图视频生产工作流

它把已经确认的历史脚本转换为与口播逐段对应的 9:16 成片，覆盖分镜、生图、配音、字符级对齐、无标点字幕、BGM、Remotion 合成和发布前 QA。

> 这不是单独运行一次命令就能自动出片的软件。Agent 负责理解脚本、拆镜、核对史实和审查画面；仓库中的脚本负责执行可重复的生产步骤。

## 固定规格

- 竖屏 1080×1920
- 30fps
- 静态信息图模式
- 实际时长由最终配音和字符级 alignment 决定
- APIMart `gpt-image-2` 1K 独立单图生成
- 默认四并发
- ElevenLabs voice ID 由每个项目显式提供
- ElevenLabs 模型默认 `eleven_v3` 也可以修改
- 字幕不含任何 Unicode 标点
- Remotion 只负责静态画面、字幕、配音、BGM 和片尾卡合成
- 候选片先进入 `out/candidates/`
- 只有用户确认后才生成 `out/final.mp4`

## 两种视觉风格

### 暖色宣纸 Vox

预设名：`warm-xuan-vox`

暖色旧宣纸、撕纸拼贴、旧地图、高密度木刻线条、低饱和土色和少量朱砂红。未指定风格时默认使用这一预设。

### 美漫 Vox

预设名：`american-comic-vox`

粗重炭黑轮廓、受控网点、角向排线、丝网印刷质感，使用青蓝、珊瑚红、芥末黄、米白和炭黑。

同一集只能使用一种预设，不能混搭，也不自动增加第三种风格。

## 工作流程

```text
确认脚本与史实
  → 拆分口播镜头和实体画面
  → ElevenLabs 配音并取得字符级 alignment
  → APIMart 为每个画面独立生图
  → 原图审查和问题帧定向重生
  → 根据 alignment 生成无标点字幕和时间轴
  → 生成或配置 BGM
  → Remotion 合成候选片
  → 检查编码 响度 黑帧 静音 字幕和画面
  → 用户确认
  → 输出 out/final.mp4
```

## Agent 兼容方式

这个仓库以 `SKILL.md` 作为工作流入口。任何能够读取本地文件、执行终端命令并调用 Python、Node.js 和 FFmpeg 的 Agent 都可以使用。

- 支持 Skill 自动发现的 Agent：把整个仓库放入该 Agent 的 Skills 目录
- 不支持 Skill 自动发现的 Agent：在任务中要求 Agent 完整读取本仓库的 `SKILL.md` 后执行
- 不使用 Agent：可以按下方命令手动运行各阶段脚本

不同 Agent 的 Skill 安装目录并不统一。本仓库不声称兼容所有产品的自动发现机制，但核心工作流和脚本不依赖 Codex 专用 API。

## 安装

### 通用安装

把仓库克隆到目标 Agent 可以访问的位置：

```bash
git clone https://github.com/snailzsh/make-static-history-video.git \
  /absolute/path/to/agent-skills/make-static-history-video
```

### Codex 安装示例

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/snailzsh/make-static-history-video.git \
  ~/.codex/skills/make-static-history-video
```

安装完成后新开一个 Codex 任务，使 Skill 被重新发现。其他 Agent 是否需要重启或重新索引，以对应产品的加载机制为准。

更新已经安装的版本：

```bash
git -C ~/.codex/skills/make-static-history-video pull --ff-only
```

### 安装运行依赖

需要：

- Python 3.11 或更高版本
- Node.js 20 或更高版本
- `ffmpeg` 和 `ffprobe`
- PingFang、黑体、微软雅黑或 Noto Sans CJK SC 中文字体之一

安装 Python 依赖：

```bash
cd /absolute/path/to/agent-skills/make-static-history-video
python3 -m pip install -r requirements.txt
```

确认媒体工具可用：

```bash
command -v ffmpeg
command -v ffprobe
```

## 配置 API Key

运行时需要两个 API Key。voice ID 可以通过环境变量或项目初始化参数提供：

```bash
export APIMART_API_KEY="你的真实 APIMart API Key"
export ELEVENLABS_API_KEY="你的真实 ElevenLabs API Key"
export ELEVENLABS_VOICE_ID="你的 ElevenLabs voice ID"
```

只把 Key 存在环境变量或本机私有配置中。不要提交 `.env`、不要把 Key 写进 `project.json`，也不要在截图或终端回显中公开。

检查变量是否存在但不显示真实值：

```bash
python3 -c 'import os; print("APIMart set" if os.getenv("APIMART_API_KEY") else "APIMart missing")'
python3 -c 'import os; print("ElevenLabs set" if os.getenv("ELEVENLABS_API_KEY") else "ElevenLabs missing")'
python3 -c 'import os; print("Voice ID set" if os.getenv("ELEVENLABS_VOICE_ID") else "Voice ID missing")'
```

## 在 Agent 中使用

新建任务，附上经过确认的脚本。支持 Skill 调用语法的 Agent 可以直接调用名称；其他 Agent 则提供 `SKILL.md` 的路径并要求完整读取。

一分钟测试：

```text
使用 $make-static-history-video 制作一集中国历史科普视频
风格使用暖色宣纸 Vox
voice ID 使用我提供的 ElevenLabs 音色
使用现有脚本的前 60 到 90 秒做测试
先输出候选片和 QA 结果
```

美漫完整版：

```text
使用 $make-static-history-video 制作历史科普完整版
风格使用美漫 Vox
voice ID 使用项目配置 模型使用 eleven_v3
时长按配音自然时长决定
完成后先交付 out/candidates 中的候选片
```

沿用默认参数：

```text
使用 $make-static-history-video 按固定工作流制作新一集
脚本已经附上
voice ID 使用 ELEVENLABS_VOICE_ID 环境变量
先核对内容和分镜再进入付费生成
```

不支持 Skill 调用语法的 Agent 可使用：

```text
完整读取 /absolute/path/to/make-static-history-video/SKILL.md
严格按其中的阶段门制作附件中的历史脚本
不要跳过生图审查 字幕零标点检查和候选片 QA
```

如果没有指定风格，Skill 使用 `warm-xuan-vox`。

## 最小输入

开始制作前至少提供：

1. 已确认的口播脚本或历史资料
2. 集数和标题
3. ElevenLabs voice ID
4. 使用暖色宣纸 Vox 或美漫 Vox
5. 先做测试版还是直接做完整版

模型、画幅和字幕规则可以省略，此时使用工作流默认值。voice ID 不再使用任何作者私人默认值，必须通过任务、命令参数或 `ELEVENLABS_VOICE_ID` 提供。

## 手动执行主要脚本

通常由 Agent 调用。需要排查单个阶段时，可以手动执行。

初始化项目：

```bash
python3 scripts/init_project.py /absolute/path/to/project \
  --title "第四集标题" \
  --voice-id "你的 ElevenLabs voice ID" \
  --visual-style warm-xuan-vox
```

生成连续配音：

```bash
python3 scripts/generate_continuous_voiceover.py \
  --project /absolute/path/to/project/project.json \
  --out /absolute/path/to/project/voice-continuous-candidate
```

连续请求失败后，按镜头边界分块：

```bash
python3 scripts/generate_chunked_voiceover.py \
  --project /absolute/path/to/project/project.json \
  --out /absolute/path/to/project/voice \
  --max-chars 430
```

生成独立信息图：

```bash
python3 scripts/generate_apimart_images.py /absolute/path/to/project
```

生成字幕和时间轴：

```bash
python3 scripts/build_aligned_captions.py \
  --project /absolute/path/to/project/project.json \
  --voice-manifest /absolute/path/to/project/voice/voiceover_manifest.json \
  --pronunciation /absolute/path/to/project/pronunciation.json \
  --caption-dir /absolute/path/to/project/captions

python3 scripts/build_timeline.py /absolute/path/to/project
```

生成 BGM 并同步 Remotion 素材：

```bash
python3 scripts/generate_original_bgm.py /absolute/path/to/project
python3 scripts/sync_remotion_assets.py /absolute/path/to/project
```

渲染候选片：

```bash
cd /absolute/path/to/project/remotion
npm install --no-audit --no-fund
npm run lint
npm run still
npm run render
```

运行项目检查：

```bash
python3 scripts/validate_project.py /absolute/path/to/project
```

## 输出结构

```text
project.json
source/original-script.md
prompts/frame-prompts.json
storyboards/production-storyboard.json
storyboards/frame-manifest.json
storyboards/timeline.json
assets/source-images/
assets/backgrounds/
voice/voiceover_full_48k.wav
voice/voiceover_manifest.json
captions/subtitles.srt
captions/caption-manifest.json
captions/overlays/
audio/music/bed.wav
out/candidates/candidate.mp4
out/qa/release.json
out/final.mp4
```

## 生产限制

- 不用旧图循环顶替新台词
- 不使用九宫格或四宫格后裁切
- 不用 Remotion 叠加场景文字修补生图错字
- 不在没有 alignment 时猜字幕时间
- 不把静态画面推拉称为动画
- 不混用不同音色或模型的配音片段
- 不接受错字、伪文字、现代旗帜、错误地图方向或跨时代建筑
- 不直接覆盖已经批准的正式文件

更完整的执行合同见 [SKILL.md](SKILL.md)，视觉、配音和 QA 细则位于 [references](references/) 目录。
