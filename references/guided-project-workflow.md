# 历史图片联播项目引导

本参考吸收 `image-story-video-wizard` 的阶段引导 状态恢复 写作包和反馈设计 但不引入它的豆包 HyperFrames 动态推拉或自由画风默认值 生产执行仍以本 Skill 的 ElevenLabs APIMart Remotion 和发布 QA 合同为准

上游设计来源 https://github.com/aaronyi97/image-story-video-wizard

## 每轮交互

简要展示当前阶段的五项信息；已有授权内可连续推进多个阶段，不为这些提示反复请求确认

- 现在进行到 当前阶段和目的
- 我现在会做 当前可以自主完成的工作
- 你现在只需要 一至三个会阻断当前阶段的输入或决定
- 完成后我会交付 可以检查的文件或预览
- 确认后下一步 下一阶段名称 不提前执行

不要让用户选择工作流下一步 不问泛化的接下来做什么 从现有文件和 `project.json.workflow` 恢复后直接提出最小请求

## 阶段顺序

```text
START
→ BRIEF
→ BENCHMARKS
→ WRITING_PACK
→ SCRIPT
→ FACT_CHECK
→ PRODUCTION_CONTRACT
→ STORYBOARD
→ VOICE
→ VISUAL_STYLE
→ CHARACTER_ANCHORS
→ IMAGE_PROMPTS
→ IMAGE_GENERATION
→ ASSET_QC
→ MUSIC
→ CANDIDATE
→ RELEASE_QA
→ FINAL_PROMOTION
→ FEEDBACK
```

已有定稿材料时检查后从最早未完成阶段恢复 前置阶段只有在确实不适用时才标记 `已跳过` 不伪造已完成产物

## 阶段合同

| 阶段 | 系统动作 | 证明产物 | 迁移门 |
|---|---|---|---|
| START | 定位项目根目录 检查宿主能力 识别新建或续做 | 项目状态摘要 | 根目录和恢复点正确 |
| BRIEF | 明确题目 受众 平台 时长 画幅 叙事目标和成功标准 | `brief.md` | 用户确认方向 |
| BENCHMARKS | 找二至五个对标 分配产品 文案 画面或反例角色 | `benchmarks.md` | 用户确认学习与避免项 |
| WRITING_PACK | 汇总任务 资料 来源 对标样本 结构 语言 长度和禁补字规则 | `writing-pack/manifest.md` | 用户确认写作方向 |
| SCRIPT | 路由到当前真实可用的写作能力 生成一份完整初稿并做一次聚焦修复 | `source/original-script.md` | 用户确认完整口播 |
| FACT_CHECK | 核查人物 时间 地理 制度 战争方向和因果 把事实 判断 未知分开 | `source/fact-check.md` | P0 事实问题为零 |
| PRODUCTION_CONTRACT | 锁定单一视觉预设 配音 字幕 画幅 生成批次 成本和验收范围 | `project.json` 与分镜草案 | 用户确认付费范围和质量门 |
| STORYBOARD | 先建立配音所需的内容镜头 `project.json.shots` 和实体帧草案 不在此阶段猜最终秒数 | `storyboards/production-storyboard.json` `storyboards/frame-manifest.json` | 用户确认内容分镜和代表性段落 |
| VOICE | 从已确认的 shots 连续生成 ElevenLabs 配音和 alignment 必要时按镜头分块 再据此生成精确时间轴 | `voice/voiceover_manifest.json` `storyboards/timeline.json` | 完整听审和接缝检查通过 |
| VISUAL_STYLE | 只在四个预设中选择一个 登记参考用途与压力帧计划 此阶段不提前生成 strict 角色场景 | 单一风格与压力帧计划 | 风格符合当前合同 |
| CHARACTER_ANCHORS | 识别重复人物 为需要严格一致性的角色建立人物卡 脸部母版和全身母版 非重复角色可跳过 | `characters/character-manifest.json` `characters/anchors/` | 必需母版均经用户确认 或明确跳过 |
| IMAGE_PROMPTS | 逐帧生成提示词 `required_text` 和必要的 `text_plan` | `prompts/frame-prompts.json` | 提示词与帧编号一一对应 |
| IMAGE_GENERATION | 母版确认后先做钩子 人物 地图 文字压力帧 样图通过后按已批准范围独立单图四并发 保存原图 台账和哈希 | `assets/source-images/` `assets/backgrounds/` | 全部实体帧存在 |
| ASSET_QC | 原尺寸检查语义 史实 地理 时代 文字 安全区和风格 | 冻结 frame manifest 与 repair 日志 | P0 P1 图像问题为零 |
| MUSIC | 选择原创或可追溯授权 BGM 或明确跳过 | `audio/music/bed.wav` 或跳过记录 | 用户确认或跳过 |
| CANDIDATE | 用 Remotion 静态切镜组装候选 不晋级正式文件 | `out/candidates/*.mp4` | 候选存在且可播放 |
| RELEASE_QA | 检查编码 响度 真峰值 黑帧 静音 字幕 配音重叠和每个切点 | `out/qa/release.json` `out/qa/voice-continuity-review.json` | 全部 P0 P1 为零 |
| FINAL_PROMOTION | 展示候选与报告 取得当前确认后才写正式路径 | `out/final.mp4` | 用户验收候选 |
| FEEDBACK | 记录真实生产时间 人工介入和平台数据 | `feedback/latest.md` | 无自动迁移 |

## 写作包规则

- 对标学习选题机制 钩子 结构 节奏 转场 语言和观众需求 不复制原句 画面 音频或成片
- 写作包必须自包含 并保留可追溯资料来源 不能只放形容词式风格要求
- 初稿字数不足或内容空洞时 回到资料和场景供给修复写作包 再开新写作轮次 不在原稿上机械填充
- 初稿大体可用时只修改明确问题 不连续整篇重写
- 三至五篇稳定成稿后 才考虑提取频道专用写作模板

## 状态规则

- `project.json` 始终是唯一真实源 `workflow` 不复制生产参数和 QA 结果
- 新选题用 `init_project.py --guided` 初始化 `voice_id` `visual_style` 和平台可暂未确定 `settings_confirmed` 必须为 false 直到 `PRODUCTION_CONTRACT` 明确确认
- 状态只允许 `未开始` `进行中` `待确认` `已确认` `需要返工` `已跳过`
- 只有当前阶段为 `已确认` 或 `已跳过` 时才能进入下一阶段
- 任一阶段返工时回到最早受影响阶段 后续产物保留但视为未重新验证 不删除
- 严格连续角色的母版未确认时 `IMAGE_PROMPTS` 和 `IMAGE_GENERATION` 不得开始 人物首次出现和后续出现都必须引用同一角色 ID 与已确认母版
- 状态确认本身不创造付费、私人数据读取、正式晋级或发布授权；已有明确批准在同目标、同内容、同数量和成本范围内持续有效，引用原依据后继续，不因阶段或 Skill 切换重复询问
- `FINAL_PROMOTION` 只有 `approvals.qc_passed` 为 true `approvals.final_promotion` 为 true 且 `out/final.mp4` 存在时才能标记为 `已确认`

使用 `scripts/manage_workflow.py` 为旧项目补充状态 校验 摘要 标记和顺序迁移
