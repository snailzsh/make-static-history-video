# 视觉提示词合同

## 风格选择

只允许选择一个预设 未指定时使用 `warm-xuan-vox` 不得混搭

### warm-xuan-vox

- 暖色旧宣纸和纸纤维
- 明显撕纸边和真实纸层阴影
- 符合目标年代的旧地图和高密度黑褐木刻线条
- 低饱和土褐 灰绿 暗棕
- 朱砂红只做少量路线 箭头 标签或单一焦点
- 禁止美漫网点 亮色块 纪念碑谷 复古报纸 现代扁平和 3D

### american-comic-vox

- 粗重手绘炭黑轮廓
- 受控 Ben Day 网点 角向排线 丝网印刷和轻微套色偏移
- 哑光青蓝 珊瑚朱红 芥末黄 米白 炭黑的大色块
- 历史编辑插画而非超级英雄漫画
- 禁止棕色宣纸单色滤镜 对话气泡 英文拟声词 霓虹色和爆炸贴纸

## 基础模板

```text
Use case: infographic-diagram plus historical scene
Asset type: vertical static infographic frame for a Chinese history documentary
Frame: {frame_id}
Narrative meaning to communicate: {shot_voiceover_context}
Primary request: {single_visual_action}
Style preset: {warm-xuan-vox or american-comic-vox exactly one}
Style contract: {copy the full selected preset constraints above}
Composition: strict 9:16 for 1080x1920 main information between top 8 percent and 76 percent bottom 22 percent low detail for subtitles
Approved readable labels exactly once: {labels}
Historical constraints: {period clothing weapons architecture fortification transport map scope}
No unspecified text no pseudo text no watermark no signature no modern administrative boundary no modern object
```

## 文字纪律

- 从 `image_text` 中只提取引号内真正需要渲染的标签
- 位置词如 中央 左 右 上 下 旁 不得进入图像
- 文字总量建议不超过 20 字
- 只使用厚重木刻宋体或篆刻字形
- 数字使用中文形式如 前二〇二年 三十二万
- 生僻人名不强行写进图像 由口播和字幕承担
- 图内错字是发布阻断 不是风格瑕疵
- 图内批准标签可保留必要标点 字幕无标点规则不适用于图内标签

## 地图和方向

- 每张地图说明上北下南或明确其它朝向
- 路线起点终点 箭头方向 颜色含义与台词一致
- 不用现代省界或国界伪装古代政权范围
- 不把台湾主岛用在香港岛语境
- 不把未核定的旗帜或现代民族国家符号放入古代场景

## 时代建筑

每帧明确目标年代 地区和可以出现的建筑 服饰 兵器 旗帜及交通工具 不使用后世常见形象代替早期史实

例如秦汉边塞应使用低矮夷土障墙 木栅栏 木制望台和土筑关隘 禁止使用明代砖砌长城 垛口 石墙和瓦顶箭楼

## 审图顺序

1. 台词语义
2. 地理和方向
3. 人物时代与服饰
4. 图内文字和数字
5. 未指定伪文字和水印
6. 底部字幕安全区
7. 前后镜风格一致性
8. 是否混入另一预设或第三种风格
