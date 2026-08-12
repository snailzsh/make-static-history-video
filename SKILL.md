---
name: make-static-history-video
description: 制作中文竖屏静态历史信息图解说视频的通用生产流程 适用于任意朝代 人物 战争 制度或历史专题 仅支持暖色宣纸 Vox 和美漫 Vox 两种视觉预设 使用 APIMart gpt-image-2 独立单图生成与口播对应的历史场景 地图 路线 箭头和准确中文标签 使用用户指定的 ElevenLabs voice ID 和模型取得字符级对齐 生成无标点字幕 配置 BGM 并由 Remotion 静态切镜合成和执行发布前 QA 用于一分钟测试 完整集 画面与台词一一对应 配音 字幕 BGM 和完整成片任务
---

# 静态历史信息图视频

将经过确认的史料或生产脚本转换为可发布成片 不把整张图的轻微缩放当成动画 不让无关图片循环顶替内容对齐

## 运行前检查

- Python 3.11 或更高版本 并安装 `requirements.txt`
- Node.js 20 或更高版本
- `ffmpeg` 和 `ffprobe` 必须能从 `PATH` 找到
- 系统需安装 PingFang 黑体 微软雅黑或 Noto Sans CJK SC 之一 也可在字幕命令中使用 `--font` 指定字体文件
- 只从环境变量读取 `APIMART_API_KEY` 和 `ELEVENLABS_API_KEY` voice ID 可由 `--voice-id` 或 `ELEVENLABS_VOICE_ID` 提供

```bash
python3 -m pip install -r requirements.txt
command -v ffmpeg
command -v ffprobe
```

## 默认生产合同

- 竖屏 9:16 1080×1920 30fps
- `static-infographic` 静态信息图模式
- 视觉预设只能二选一 `warm-xuan-vox` 或 `american-comic-vox`
- 未指定风格时默认 `warm-xuan-vox`
- APIMart `gpt-image-2` 1K 独立单图 默认四并发 禁止宫格
- 每个项目必须提供 ElevenLabs voice ID 模型默认 `eleven_v3` 也可显式指定
- 台词信息 地图 路线 战争方向 章节文字直接烘焙进生成图
- Remotion 只组装静态图 字幕 配音 BGM 和经批准的片尾卡
- ElevenLabs 必须返回字符级 alignment
- 实际时长由配音决定 不硬凑 60 秒或 10 分钟
- 图像底部 22% 保留低细节 字幕位于底部 18% 安全区
- 字幕删除全部 Unicode 标点 配音文本保留必要标点控制韵律
- 先输出 `out/candidates/` 候选 通过 QA 后才晋级 `out/final.mp4`

用户明确指定其它非风格参数时以用户参数为准并把偏离写入 `project.json` 第三种视觉风格不视为普通参数偏离 必须先修改固定合同

## 工作流

### 1 锁定内容和视觉合同

1. 读取原文 史料 脚本和用户要求
2. 核定时间 人物 地理 战争方向 制度和因果表述
3. 把确认事实与分析判断分开 没有依据不补齐
4. 写入 `project.json` 并生成生产分镜
5. 只在内容和视觉合同确认后进入付费生成

初始化项目

```bash
python3 scripts/init_project.py /absolute/project/path \
  --title "视频标题" \
  --voice-id "用户的 ElevenLabs voice ID" \
  --model-id "eleven_v3"
```

读取 [project-contract.md](references/project-contract.md) 创建目录 分镜和 manifest

### 2 把口播拆成镜头和信息图

- 一张图只承担一个核心信息动作
- 建立 `shot_id` 配音段落与 `frame_id` 实体图片的明确关系
- 每张图指定 `start` 或 `on_word` 锚点
- `on_word` 必须原样出现在 TTS 文本中
- 快切多帧使用独立实体资产和 `hold_seconds`
- 不允许一张无关图在多段台词中循环
- 脚本标注秒数只是节奏参考

### 3 生成配音

1. 先试单次连续 `with-timestamps` 请求
2. 单次请求超时或断开时 只能在镜头边界分块降级
3. 分块时保持相同 voice ID model ID stability seed 策略和文本顺序
4. 不自动在每个 chunk 之间插入停顿 只添加脚本明确要求的停顿
5. 保存完整 manifest 全局镜头时间 chunk 映射 request ID 文本哈希和字符对齐
6. 如需 `atempo` 后加速 必须同比缩放 alignment 时间

```bash
python3 scripts/generate_continuous_voiceover.py \
  --project project.json --out voice-continuous-candidate
```

连续请求成功后 将该候选复制为规范 `voice/` 目录 连续请求失败时保留失败日志 将候选目录归档 然后向空的 `voice/` 目录生成分块降级版

```bash
python3 scripts/generate_chunked_voiceover.py \
  --project project.json --out voice \
  --max-chars 430 --speed 1.0 --post-speed 1.0
```

不把 API key 写入技能或日志 仅从 `ELEVENLABS_API_KEY` 环境变量读取

配音细则读取 [voice-and-captions.md](references/voice-and-captions.md)

### 4 生成并审查信息图

1. 选择且只选择一个视觉预设
   - `warm-xuan-vox` 暖色宣纸 撕纸拼贴 旧地图 高密度木刻线条 低饱和土色和少量朱砂红
   - `american-comic-vox` 粗重炭黑轮廓 受控网点印刷 青蓝 珊瑚红 芥末黄 米白和炭黑
2. 不混搭两种预设 不提供纪念碑谷 复古报纸或第三种默认风格
3. 先生成四类压力测帧 钩子 人物 复杂地图 高密度文字
4. 通过后再以1K独立单图四并发生成其余图片 禁止宫格裁切
5. 每张保存服务原图和 1080×1920 RGB canonical PNG
6. 保存 task ID 耗时 成本 原尺寸 canonical 尺寸和 SHA256
7. 生图失败时只重试当前帧 不用邻帧冒充
8. 用 `view_image` 原尺寸审查文字 方向 地理 时代符号 字幕安全区和重复元素
9. 错字 伪字 越界或时代错误必须定向重生当前帧 保留失败候选和 repair 日志
10. 不用 Remotion 叠字掩盖生图错误

读取 [visual-prompt-contract.md](references/visual-prompt-contract.md) 构建提示词

```bash
python3 scripts/generate_apimart_images.py /absolute/project/path
```

### 5 根据 alignment 生成字幕和镜头时轴

```bash
python3 scripts/build_aligned_captions.py \
  --project project.json \
  --voice-manifest voice/voiceover_manifest.json \
  --pronunciation pronunciation.json \
  --caption-dir captions

python3 scripts/build_timeline.py /absolute/project/path
```

- 字幕使用批准后的正字 不显示 TTS 谐音替代字
- 字幕生成前删除全部 Unicode 标点符号 最终扫描命中数必须为 0
- 单条建议不超过 16 个中文字符
- 时间轴必须连续无重叠 分块尾静音由前一张图承接
- 把字幕预渲染为透明 PNG 避免渲染机字体差异

### 6 生成 BGM 并合成

优先使用原创或已确认授权的音乐 未确定版权时可生成原创程序化氛围床

```bash
python3 scripts/generate_original_bgm.py /absolute/project/path
python3 scripts/sync_remotion_assets.py /absolute/project/path
cd /absolute/project/path/remotion
npm install --no-audit --no-fund
npm run lint
npm run still
npm run render
```

静态版禁止背景呼吸 整图推拉 Ken Burns 视差漂浮或装饰性动画 只使用硬切或克制的静态转场

### 7 发布前 QA

1. 先检查所有源资产和 manifest
2. 先渲染首帧 中段 复杂地图 关键错字帧 揭晓帧和片尾帧
3. 候选片渲染完成后运行媒体和内容双重检查
4. 任何 P0 或 P1 不通过时不得复制到 `out/final.mp4`
5. 修复后重新运行受影响阶段和最终检查

```bash
python3 scripts/validate_project.py /absolute/project/path
```

完整命令和阈值读取 [release-qa.md](references/release-qa.md)

## 阶段门

- S0 内容合同 史实 脚本 视觉定稿
- S1 配音 音色模型正确 alignment 完整 无异常断点
- S2 生图 数量尺寸正确 台词语义一一对应
- S3 字幕 正字 时轴 安全区和可读性正确
- S4 Remotion 编译和关键帧通过
- S5 候选成片的编码 黑帧 静音 响度 裁切 字幕通过
- S6 正式输出哈希与 QA 报告完整

## 必要产物

```text
project.json
source/original-script.md
storyboards/production-storyboard.json
storyboards/frame-manifest.json
storyboards/timeline.json
prompts/frame-prompts.json
assets/source-images/
assets/backgrounds/
voice/voiceover_full_48k.wav
voice/voiceover_manifest.json
captions/subtitles.srt
captions/caption-manifest.json
audio/music/bed.wav
out/candidates/candidate.mp4
out/qa/release.json
out/final.mp4
```

## 发布文案

按平台分别写微信公众号 抖音和 X 文案 标题不使用标点符号 正文保留必要标点 读取 [publishing-copy.md](references/publishing-copy.md)

## 禁止行为

- 不用旧图循环冒充新台词
- 不把 Remotion 文字叠加当成场景生图
- 不在没有 alignment 时猜字幕时间
- 不把全屏缩放或轻微平移宣称为动画
- 不混用不同 voice ID model ID 或未标记候选配音
- 不使用明代砖长城表示秦汉初年的夷土障塞
- 不接受错字 伪文字 现代旗帜 错位岛屿和相反方向
- 不直接覆盖已经批准的 `out/final.mp4`
- 不使用 hybrid layered 拆层动画或把静态推拉宣称为动画
- 不使用九宫格 四宫格或本地裁格
- 不自动增加第三种风格或混合两种固定预设
