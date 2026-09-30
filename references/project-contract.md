# 项目合同与数据结构

## 目录

1. 单一真实源
2. 镜头和帧
3. 时间与片尾
4. 状态字段

## 单一真实源

`project.json` 是项目级参数和批准状态的唯一真实源

`project.json.workflow` 保存从选题到发布反馈的引导状态 包括当前阶段 各阶段状态 待确认问题 已登记产物和迁移历史 它只描述进度 不复制 `settings` `voice` `approvals` `shots` 中的生产事实

用户说继续或可以应结合当前具体预览和既有授权判断；状态字段不自动创造付费、晋级或发布授权。已经明确批准且范围未变的工作持续执行，不逐阶段重复请求批准。

`project.json.settings.visual_style` 只允许 `warm-xuan-vox` `american-comic-vox` `knowledge-card` 或 `qibaishi-xieyi`

缺省为 `warm-xuan-vox` 项目合同可覆盖默认值 不得在同一项目中同时声明多种风格

`project.json.settings.subtitle_mode` 只允许 `rendered` 或 `none` `none` 表示保留 alignment 和 SRT 侧车但不渲染字幕

`storyboards/production-storyboard.json` 保存内容镜头

`storyboards/frame-manifest.json` 保存每个实体图片资产

`characters/character-manifest.json` 保存角色 ID 连续性级别 人物卡 身份锁定描述和母版路径 角色外貌缺乏史料时必须标注为生产设计 不得冒充历史肖像

`voice/voiceover_manifest.json` 是最终时长和镜头音频边界的唯一真实源

`out/qa/voice-continuity-review.json` 记录全片听审和分块接缝听审结果 `result` 不为 `pass` 时不得将 `voice_continuity_passed` 或 `qc_passed` 设为 true

`storyboards/timeline.json` 只能从 voice manifest 和字符 alignment 生成

不保留多套字段冲突的 storyboard 不让 renderer 自行选源

## 镜头和帧

`project.json` 中每个 shot 至少包含

```json
{
  "shot_id": "s01",
  "name": "钩子",
  "voiceover_text": "TTS 实际文本",
  "caption_parts": ["字幕正字文本"]
}
```

`frame-manifest.json` 中每个实体图片至少包含

```json
{
  "shot_id": "s01",
  "frame_id": "F01",
  "anchor_word": null,
  "character_ids": ["C01"],
  "scene": "画面要表达的唯一核心动作",
  "image_text": "反"
}
```

`continuity: strict` 的角色必须同时具备已确认的脸部母版和全身母版 场景帧中的 `character_ids` 会触发生图前校验并自动注入对应身份提示词和母版参考图

`continuity: descriptive` 用于只出现一次或远景角色 只继承人物卡文字 不要求付费生成母版

`anchor_word: null` 表示镜头开始

其他值必须与 TTS 文本完全一致

快切多帧使用相同 `anchor_word` 和顺序 `hold_seconds`

```json
{
  "shot_id": "s44",
  "frame_id": "F91a",
  "anchor_word": "三十二万人",
  "hold_seconds": 0.4
}
```

## 时间与片尾

片尾特殊节奏写入 `project.json`

```json
{
  "ending": {
    "after_frame": "F91c",
    "episode": "01",
    "next_title": "白登山七天七夜",
    "black_on_word": "亲爹"
  }
}
```

## 状态字段

只有产物确实存在且检查通过时才将对应 approval 改为 true

`flow_generated` 在不使用 Flow 的项目中保持 false 不把它当成失败

`motion_assets_ready` 和 `motion_preview_confirmed` 在静态版中保持 false

`qc_passed` 必须最后更新

`voice_continuity_passed` 只能在最终配音全片 1× 听审 每个 chunk 接缝复听且无重叠旁白后更新
