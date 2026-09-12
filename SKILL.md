---
name: make-static-history-video
description: 从选题 对标研究 写作包和史实核查开始 制作中文静态历史信息图解说视频 正篇默认竖屏也支持用户明确指定的横版番外 支持四种固定视觉预设 使用 APIMart gpt-image-2 独立生图 ElevenLabs 连续配音与字符级对齐 Remotion 静态切镜 并检查配音连续性 逐切点和发布质量
---

# 静态历史信息图视频

从新选题或已有材料恢复到正确阶段 将经过确认的史料或生产脚本转换为可发布成片 不把整张图的轻微缩放当成动画 不让无关图片循环顶替内容对齐

## 项目引导与恢复

新选题 缺少定稿脚本 或用户要求从头推进时 先读取 [guided-project-workflow.md](references/guided-project-workflow.md)

- 用 `project.json.workflow` 记录当前阶段 各阶段状态 待确认问题 产物路径和历史 不创建第二套项目状态源
- 每轮只推进当前阶段 明确现在进行到什么 系统会做什么 用户只需确认什么 将交付什么以及确认后的下一步
- 对标与写作包阶段可调用现有的对标拆解 转写 搜索或写作能力 但不得声称未实际使用的模型或宿主已经参与
- `SCRIPT` `FACT_CHECK` 和 `PRODUCTION_CONTRACT` 均确认前 不进入付费配音或批量生图
- 重复人物必须经过独立的 `CHARACTER_ANCHORS` 阶段 需要严格一致性的角色未确认脸部与全身母版前 不得进入场景批量生图
- 旧项目没有 `workflow` 字段时 可用 `scripts/manage_workflow.py init` 非破坏地补充 新选题使用 `init_project.py --guided` 创建 此时不提前确认音色 画风和平台
- 阶段状态只能是 `未开始` `进行中` `待确认` `已确认` `需要返工` `已跳过` 用户说继续只批准当前展示的确认门

```bash
python3 scripts/manage_workflow.py summary /absolute/project/path
python3 scripts/manage_workflow.py validate /absolute/project/path
```

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

- 正篇默认竖屏 9:16 1080×1920 30fps 用户明确指定的番外可以使用原生横版 16:9 1920×1080
- `static-infographic` 静态信息图模式
- 视觉预设只能四选一 `warm-xuan-vox` `american-comic-vox` `knowledge-card` 或 `qibaishi-xieyi`
- 未指定风格时默认 `warm-xuan-vox`
- APIMart `gpt-image-2` 1K 独立单图 默认四并发 禁止宫格
- 每个项目必须提供 ElevenLabs voice ID 模型默认 `eleven_v3` 也可显式指定
- 台词信息 地图 路线 战争方向 章节文字直接烘焙进生成图
- Remotion 只组装静态图 字幕 配音 BGM 和经批准的片尾卡
- ElevenLabs 必须返回字符级 alignment
- 实际时长由配音决定 不硬凑 60 秒或 10 分钟
- 图像底部 22% 保留低细节 字幕位于底部 18% 安全区
- 字幕删除全部 Unicode 标点 配音文本保留必要标点控制韵律 字幕可按 `subtitle_mode` 渲染或仅保留 SRT 侧车
- 最终配音必须通过全片 1× 听审 分块接缝复听和重叠检查 不接受断气 断字 重字 音色跳变或多音轨重叠
- 先输出 `out/candidates/` 候选 通过 QA 后才晋级 `out/final.mp4`

用户明确指定其它非风格参数时以用户参数为准并把偏离写入 `project.json` 新增第五种视觉风格不视为普通参数偏离 必须先修改固定合同

## 工作流

### 0 选题 对标 写作包和脚本

1. 把用户想法整理为平台 受众 题目 时长 画幅和成功标准明确的 brief
2. 为二至五个对标分别指定产品模式 文案配音 画面或反例角色 学结构和节奏 不复制原文 成片或声音
3. 建立自包含写作包 保存资料来源 对标样本 结构节奏规则 长度要求和禁止补字要求
4. 生成一份完整初稿 大体可用时只做一次聚焦修复 严重空洞或字数不足时回到写作包后重新生成 不在坏稿上填充
5. 用户确认脚本后单独进行史实核查 把可验证事实 分析判断和未确认项分开
6. 史实与生产合同确认后 才进入下方付费生产步骤

完整阶段 状态迁移和产物规则读取 [guided-project-workflow.md](references/guided-project-workflow.md)

### 1 锁定内容和视觉合同

1. 读取原文 史料 脚本和用户要求
2. 核定时间 人物 地理 战争方向 制度和因果表述
3. 把确认事实与分析判断分开 没有依据不补齐
4. 写入 `project.json` 并生成生产分镜
5. 只在内容和视觉合同确认后进入付费生成

初始化项目

```bash
python3 scripts/init_project.py /absolute/project/path \
  --title "新选题" --guided

# 已有定稿生产合同时
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
7. 生成后必须完整听审 并对每个 chunk 接缝前后至少 3 秒复听 有断气 断字 重字 漏字 点击声 音色或节奏跳变时只重生受影响 chunk
8. 不用旧音色 SRT 逐条生成新音色 更换音色后从新音频重建 alignment SRT 和镜头时轴

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
   - `knowledge-card` 一页式历史百科知识卡片 暖宣纸撕纸拼贴 白边人物与器物 地图 数据 时间轴 关系图和准确中文讲解卡 所有可见文字容器都有内容 禁止空白标签框
   - `qibaishi-xieyi` 先从当前内容推导独有情境 再以齐白石式写意精神组织笔墨 留白和少量内容必需的颜色 不复用固定人物 道具 象征物或构图
2. 不混搭四种预设 不提供纪念碑谷 复古报纸或未经批准的第五种风格
3. 新项目和返工帧先按 `visual-prompt-contract.md` 建立 `prompt_contract_version: 2` 结构化场景合同 把抽象概念转换为目标年代可直接画出的现实场景 并运行 `validate_frame_prompts.py` 通过付费前预检
4. 先生成四类压力测帧 钩子 人物 复杂地图 高密度文字
5. 通过后再以1K独立单图四并发生成其余图片 禁止宫格裁切
6. 每张保存服务原图和 1080×1920 RGB canonical PNG
7. 保存 task ID 耗时 成本 原尺寸 canonical 尺寸和 SHA256
8. 生图失败时只重试当前帧 不用邻帧冒充
9. 用 `view_image` 原尺寸审查文字 方向 地理 时代符号 字幕安全区和重复元素
10. `knowledge-card` 必须对照 `text_plan` 检查每个文字容器 空白文字框数必须为零
11. 错字 伪字 空白文字框 越界或时代错误必须定向重生当前帧 保留失败候选和 repair 日志 基础场景含错误诱因时完整重写场景合同 不在旧提示词后继续堆否定句
12. 不用 Remotion 叠字掩盖生图错误

人物连续性先读取 [character-continuity.md](references/character-continuity.md) 建立人物卡和母版 再读取 [visual-prompt-contract.md](references/visual-prompt-contract.md) 构建逐帧提示词

生成已确认的人物脸部与全身母版时 可复用同一 APIMart 脚本并指定独立目录

```bash
python3 scripts/generate_apimart_images.py /absolute/project/path \
  --prompt-file characters/anchor-prompts.json \
  --raw-dir characters/source-anchors \
  --canonical-dir characters/anchors \
  --report-file logs/apimart-character-anchors.json
```

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
- SRT 只描述当前最终音频的对齐 不是更换音色的生成时间表
- `subtitle_mode: none` 时仍生成完整 SRT 侧车 但 Remotion 不渲染 overlay 且候选片字幕流为 0
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

最终 H.264 编码时必须在 timeline 的每个画面起始帧强制关键帧 不得只依赖编码器的自动场景切换判断

### 7 发布前 QA

1. 先检查所有源资产和 manifest
2. 先渲染首帧 中段 复杂地图 关键错字帧 揭晓帧和片尾帧
3. 候选片渲染完成后运行媒体和内容双重检查
4. 完整以 1× 速度听审旁白 并将分块接缝 断气 断字 重字 漏字 音色节奏跳变和语音重叠结果写入 `out/qa/voice-continuity-review.json`
5. 运行全切点检查 逐一验证前后帧内容 PTS 连续性和切点关键帧
6. 只有 `voice-continuity-review.json` 为 pass 且全部技术检查通过才能将 `voice_continuity_passed` 和 `qc_passed` 设为 true
7. 任何 P0 或 P1 不通过时不得复制到 `out/final.mp4`
8. 修复后重新运行受影响阶段和最终检查

```bash
python3 scripts/validate_project.py /absolute/project/path
python3 scripts/qa_cut_boundaries.py /absolute/project/path --candidate out/candidates/candidate.mp4
```

完整命令和阈值读取 [release-qa.md](references/release-qa.md)

## 阶段门

- S0 内容合同 史实 脚本 视觉定稿
- S1 配音 音色模型正确 alignment 完整 无断气不连贯 无异常断点 无重叠旁白 完整听审通过
- S2 生图 数量尺寸正确 台词语义一一对应
- S3 字幕 正字 时轴 安全区和可读性正确
- S4 Remotion 编译和关键帧通过
- S5 候选成片的编码 黑帧 静音 响度 裁切 字幕通过
- S6 正式输出哈希与 QA 报告完整

## 必要产物

从新选题启动时 上游阶段还应保留 `brief.md` `benchmarks.md` `writing-pack/` `source/original-script.md` `source/fact-check.md`；已有定稿脚本启动时 可将不适用阶段明确标记为 `已跳过`

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
out/qa/voice-continuity-review.json
captions/subtitles.srt
captions/caption-manifest.json
audio/music/bed.wav
out/candidates/candidate.mp4
out/qa/release.json
out/final.mp4
```

## 发布文案

按平台分别写微信公众号 抖音和 X 文案 标题不使用标点符号 正文保留必要标点 读取 [publishing-copy.md](references/publishing-copy.md)

成片发布后 如果用户提供真实平台数据 进入 `FEEDBACK` 阶段 记录实际制作时长 人工介入 播放 留存 互动和收益 只提出下一集最小可验证改动 不用一次成片或一次爆帖冻结频道模板

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
- 不用旧 SRT 时间码逐条生成新音色并将重叠语音视为可接受结果
- 不自动增加第五种风格或混合四种固定预设
