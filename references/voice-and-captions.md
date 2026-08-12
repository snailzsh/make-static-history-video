# 配音和字幕

## ElevenLabs

请求 `POST /v1/text-to-speech/{voice_id}/with-timestamps`

普通 Create Speech 只返回音频 不能直接支撑字符级字幕

对每次请求记录 voice ID model ID language stability seed request ID 原文 音频路径和 alignment

本系列默认使用 `DowyQ68vDpgFYdWVGjc3` 与 `eleven_v3` 用户明确指定其他参数时才偏离并记录到 `project.json`

## 谐音文本

TTS 文本可为改善发音使用谐音字

字幕必须显示标准正字

在 `pronunciation.json` 记录正字到 TTS 文本的映射 并用序列对齐还原时间

## 分块降级

- 仅在镜头边界分块
- 保持相同音色和模型
- 每块建议 300 到 500 个中文字符 再根据 API 稳定性调整
- 不在分块边界默认加静音
- 脚本停顿写入 `voice.scripted_pauses`
- 保存 chunk 到 shot 的显式映射
- 废弃候选不得和最终候选混在同一目录

## 速度

ElevenLabs 当前产品文档明确写明 `eleven_v3` 不支持 Speed 设置 因此 v3 请求不发送该字段 需要加速时使用生成后的 `atempo`

不相信 API 已接受 speed 字段就代表速度实际改变

测量自然输出时长后再决定是否使用 `atempo`

后加速后 alignment 每个时间值按实测音频比例缩放

## 字幕

- 删除全部 Unicode 标点符号 最终 manifest SRT 和 overlay 文本扫描命中数必须为 0
- 单 cue 不超过 16 个中文字符
- 语义断句优先于固定字数
- 建议字号 64px 适用于 1080×1920
- 位于底部安全区 保留左右至少 40px 底部至少 120px
- 可使用 PingFang SC Noto Sans CJK SC Microsoft YaHei 后备
- 预渲染 RGBA overlay 并检查 alpha bbox
