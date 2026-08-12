# 发布 QA

## 媒体目标

- H.264 视频
- AAC 48kHz 音频
- 1080×1920
- 30fps
- 总帧数与 timeline 一致
- 集成响度目标 -16 LUFS 允许 ±0.5 LU
- 真峰值不高于 -1.5 dBTP
- 无非预期黑帧
- 无超过 0.6 秒的非脚本静音
- 字幕 Unicode 标点命中数为 0
- 视觉风格只命中项目选择的一个预设

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
```

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
- 无 alignment 的猜测时轴
- 过峰音频 非预期长静音 音乐压过人声
- 候选还未通过 QA 就覆盖 `out/final.mp4`
- 同一项目混入两种固定视觉预设或第三种风格
