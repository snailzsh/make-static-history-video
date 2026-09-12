# 发布 QA

## 媒体目标

- H.264 视频
- AAC 48kHz 音频
- 分辨率必须等于 `project.json.settings.canvas` 正篇默认 1080×1920 用户明确指定的横版可为 1920×1080
- 30fps
- 总帧数与 timeline 一致
- timeline 所有相邻画面无空洞无重叠
- 每个画面起始帧都是 H.264 关键帧
- 每个切点前一帧属于上一张图 切点帧属于下一张图
- 所有切点前后 PTS 仍严格保持 30fps 连续
- 集成响度目标 -16 LUFS 允许 ±0.5 LU
- 真峰值不高于 -1.5 dBTP
- 无非预期黑帧
- 无超过 0.6 秒的非脚本静音
- 字幕 Unicode 标点命中数为 0
- 视觉风格只命中项目选择的一个预设
- 最终旁白全片 1× 听审通过 每个 chunk 接缝前后至少 3 秒已复听
- 未预期换气 断字 重字 漏字 音色节奏跳变和重叠旁白为 0
- `out/qa/voice-continuity-review.json` 的 `result` 为 `pass`
- `subtitle_mode: none` 时候选片字幕流数为 0 但 alignment 和 SRT 侧车仍完整

## 命令

```bash
ffprobe -v error -count_frames \
  -show_entries format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,nb_read_frames,sample_rate,channels \
  -of json out/candidates/candidate.mp4

ffmpeg -hide_banner -i out/candidates/candidate.mp4 \
  -vn -af loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json -f null -

ffmpeg -hide_banner -i out/candidates/candidate.mp4 \
  -vf "blackdetect=d=0.25:pix_th=0.05" -an -f null -

ffmpeg -hide_banner -i out/candidates/candidate.mp4 \
  -af "silencedetect=noise=-50dB:d=0.4" -vn -f null -

ffmpeg -hide_banner -i out/candidates/candidate.mp4 \
  -vf "fps=1/30,scale=216:384:flags=lanczos,tile=5x5" \
  -frames:v 1 out/qa/contact-sheet.png

python3 scripts/qa_cut_boundaries.py /absolute/project/path \
  --candidate out/candidates/candidate.mp4
```

## 切点防卡顿

- 渲染阶段用 `-force_key_frames` 按 timeline 的每个 `start_frame / fps` 生成关键帧
- 不得用总帧数正确替代切点检查 总帧数正确仍可能有延迟换图或非关键帧切换
- `qa_cut_boundaries.py` 必须对每个相邻画面检查 timeline 连续 PTS 连续 关键帧和解码后内容归属
- 任何切点缺关键帧 出现重复帧 黑帧 跳帧或延迟换图都是发布阻断

## 视觉必查帧

- 首帧钩子
- 人物名称最多的一帧
- 最复杂路线图
- 数字最多的一帧
- 曾经出现错字的修复帧
- 时代建筑风险帧
- 揭晓帧
- 片尾快切和黑帧边界

## 发布阻断

以下任一项出现就不得晋级正式文件

- 缺图或重复图顶替
- 台词和画面相反
- 地图方向错误
- 人名地名数字错字
- 明显跨时代建筑旗帜或交通工具
- 字幕遮挡人脸关键道具或越界
- 配音音色或模型混用
- 最终旁白未完整听审 或 `voice-continuity-review.json` 缺失 未通过
- 未预期换气 句内断气 断字 重字 漏字 点击声 音色或节奏突变
- 两段旁白时间重叠 或用旧 SRT 逐条生成的替换音色在剪辑软件中堆成多音轨
- 无 alignment 的猜测时轴
- 任一画面切点不在准确帧上或不是关键帧
- 过峰音频 非预期长静音 音乐压过人声
- 候选还未通过 QA 就覆盖 `out/final.mp4`
- 同一项目混入多个固定视觉预设或未经批准的第五种风格
