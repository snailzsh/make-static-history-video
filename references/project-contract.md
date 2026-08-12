# 项目合同与数据结构

## 目录

1. 单一真实源
2. 镜头和帧
3. 时间与片尾
4. 状态字段

## 单一真实源

`project.json` 是项目级参数和批准状态的唯一真实源

`project.json.settings.visual_style` 只允许 `warm-xuan-vox` 或 `american-comic-vox`

缺省为 `warm-xuan-vox` 不得在同一项目中同时声明两种风格

`storyboards/production-storyboard.json` 保存内容镜头

`storyboards/frame-manifest.json` 保存每个实体图片资产

`voice/voiceover_manifest.json` 是最终时长和镜头音频边界的唯一真实源

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
  "scene": "画面要表达的唯一核心动作",
  "image_text": "反"
}
```

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
