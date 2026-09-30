# 配音和字幕

## ElevenLabs

请求 `POST /v1/text-to-speech/{voice_id}/with-timestamps`

普通 Create Speech 只返回音频 不能直接支撑字符级字幕

对每次请求记录 voice ID model ID language stability seed request ID 原文 音频路径和 alignment

每个项目必须在初始化时提供 voice ID 模型缺省为 `eleven_v3` 也可显式指定 所有实际参数写入 `project.json` 和最终 voice manifest

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

## 音频完整性检查

接口成功、字符数组与全文相等、人工反馈“听起来正常”，都不能单独排除长响应尾部被截断。配音生成后先检查三个 alignment 数组长度、文本覆盖、时间单调、实测音频范围，以及可发音字符是否连续被钳在终点零时长。

```bash
# text-file 必须是这一请求实际发送的精确文本，含原有标点，不手工多加换行。
# duration 来自同一音频的 ffprobe；shot 局部对齐使用对应片段的实测时长。
python3 "$SKILL_ROOT/scripts/check_voice_alignment.py" voice/continuous_alignment.json \
  --text-file voice/request-text.txt --duration 123.456
```

该命令只输出技术检查结果，不写项目审批、不修改音频、不发起付费请求。分块配音逐块检查，再核对最终 manifest 的 shot 顺序、数量和合并时轴；不能拿某块的通过结果代替全片完整性。零时长字会阻断自动通过，需定位原声与原始响应，不能仅为通过检查篡改时间。

检测缺段后保留请求 ID、响应和可用前缀，按完整 shot 边界准备最小补配。新增付费未在预算内时展示补配次数、字符数和成本后再执行。不要把一次截断时长写成服务固定限制。

插入脚本停顿、合法裁剪或变速后，使用编辑映射更新所有下游字符、shot、接缝、SRT 和 timeline，保存修改前后音频哈希，再听审实际用于合成的最终版本。项目批准的模型变更不自动修改 Skill 默认模型。

## 配音连续性发布门

自动媒体指标不能证明口播流畅 最终音频必须通过完整人工听审

- 用耳机以 1× 速度完整听审最终旁白 不跳过长段落
- 对每个 chunk 接缝前后至少 3 秒单独复听 同时检查未加速源音频和加速后最终音频
- 未预期吸气或呼气 句内断气 词内断裂 首尾音节被截断 重字 漏字 点击声 爆音 音色 响度 音高 语速或节奏突变都是失败
- 任何两段旁白同时播放均是失败 必须在 voice manifest 时间区间和最终剪辑工程中同时检查重叠
- 不用交叉淡化 音乐遮盖或增大背景噪声来伪装修复不流畅接缝 只重生受影响的 chunk
- 把结果写入 `out/qa/voice-continuity-review.json` 至少记录候选音频哈希 完整听审 接缝数 失败时间码 重叠数 复核人和 `result`
- `result` 必须为 `pass` 才能将 `project.json.approvals.voice_continuity_passed` 和 `qc_passed` 设为 true

最小通过报告：

```json
{
  "candidate_audio_sha256": "<sha256>",
  "full_playback_reviewed": true,
  "chunk_joins_expected": 10,
  "chunk_joins_reviewed": 10,
  "failure_timestamps": [],
  "overlap_count": 0,
  "reviewer": "<name or agent>",
  "result": "pass"
}
```

`chunk_joins_expected` 来自 `voiceover_manifest.json.chunk_joins` 长度 连续单次请求为 0

## 更换音色与 SRT

- SRT 时间码只对应生成它的那条最终音频 不是另一个音色的配音排期
- 不把旧 SRT 切成的短 cue 逐条送入新音色 新音色的语速和停顿不同 会使生成片段溢出旧 cue 并在剪辑软件中叠成多条音轨
- 更换音色时使用带标点的完整 `voiceover_text` 生成一条连续音频 服务不稳定时才按长语义段落或镜头边界分块
- 新音频确定后从它的 alignment 重新生成 SRT 画面 timeline 和候选片 不用拉伸旧字幕硬套

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
- `subtitle_mode: none` 时仍保留 alignment 和完整 SRT 侧车 但不渲染 overlay 候选片字幕流数必须为 0
