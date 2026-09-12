# 视觉提示词合同

## 风格选择

只允许选择一个预设 未指定时使用项目合同指定的默认值 项目没有覆盖时使用 `warm-xuan-vox` 不得混搭

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

### knowledge-card

- 一页式中国历史百科知识卡片 scrapbook collage 与 paper cutout explainer
- 暖色旧宣纸 米白卡纸 撕边 白描边 真实纸层阴影 胶带 回形针和少量朱砂印章
- 人物 地图 建筑 器物 路线 箭头 时间轴 数据块 关系图和讲解卡共同构成画面
- 炭黑 深朱红 米色 铜金 旧纸黄为固定主色 极少灰绿点缀
- 主标题 核心图 讲解卡形成明确三级阅读顺序
- 每帧必须有准确主标题或核心标签 复杂帧通常有二至五组短讲解文字
- `required_text` 锁定必须逐字准确的核心文字 `text_plan` 为每个可见标题框 便签 图例 数据卡 地图标签 时间节点和印章框指定内容
- 每个看起来像文字容器的元素都必须有可读文字 空白文字框数必须为零
- 纯装饰纸片可无字 但不得画成明显的空白说明卡
- 未知 未完成 无记载或延迟揭晓必须用「尚未揭晓」「未完稿」「史无明载」等状态词表达 或改用无边框图形 不能留空框
- 可增加与台词直接相关且史实正确的中文说明 新增文字仍需逐字验收
- 禁止乱码 伪汉字 残缺字 无意义字串 随机英文 现代商业海报 纯文字 PPT 和写实 3D

### qibaishi-xieyi

- 先读出当前内容没有明说却最牵动人的情绪转折 将其化成只属于该主题的可见情境
- 画面元素 数量 距离 显现与消失均从当前台词的语义和情绪推导 不使用预设道具清单
- 以齐白石式写意精神重新理解现实 在似与不似之间抓取生命力 朴拙 天真 幽默而不轻浮
- 笔锋在行进中自然改变压力 速度 含水和含墨 一条线内可有粗细 迟疑 枯断 重接 飞白和笔尖分叉
- 墨块边缘可渗开 回缩 积聚并留下水痕 但偶然只在关键位置发生且必须服务情绪 不覆盖全画成为噪声
- 只保留传神所必需的形体 省略处与已画处共同完成内在动作
- 留白从情绪未说尽之处扩张 并由已落笔势塑形 不预设固定面积或位置
- 颜色只在内容确实需要时从墨中生出 保持单纯 鲜活和手工施染的不均匀边缘
- 稳定的电影级构图 严格使用 `project.json` 指定画幅 正篇默认九比十六 番外或用户明确指定时可为十六比九 字幕模式开启时按项目安全区保留低细节
- 接收图片时只保留不可丢失的识别依据 重组其余布局 信息和力量方向 不复制原摄影质感
- 禁止在不同主题间复用固定人物 道具 象征物 构图或留白位置
- 禁止仿冒题款 签名 印章 伪文字 水印和与当前台词无关的空泛意境

## 首轮通过率优先的提示词编译

新项目和重写帧使用 `prompt_contract_version: 2` 不直接从一段散文提示词调用生图 先为每帧建立结构化场景合同

- `narrative_goal` 只说明观众必须理解的意义
- `literal_scene` 把抽象因果改写为目标年代真实可画的一处场景
- `visual_inventory` 分别列出人物 物件和环境 并尽量给出数量 没列入清单的关键物件不主动引入
- `primary_action` 只允许一个核心动作 `action_direction` 说明动作或因果从哪里到哪里
- `model_misread_risk` 在付费前回答 如果模型只记住具体名词和动词 最可能误画成什么
- `avoid_terms_in_prompt` 保存不能进入正向场景描述的视觉诱因 只用于预检 不发送给模型
- `positive_replacements` 用明确可画的安全对象替代风险对象 必须发送给模型
- 无批准文字且存在 `unapproved_text` 风险时必须填写 `surface_contract` 逐类说明纸张 木材 墙面 天空等可见表面实际呈现的连续材质 不能只写不要文字
- `historical_constraints` 使用目标年代的正向白名单 不用后世常见形象代替

付费前运行

```bash
python3 scripts/validate_frame_prompts.py prompts/frame-prompts.json \
  --report out/qa/prompt-preflight.json
```

预检失败不得调用生图接口 修复时不能只追加新的否定句 如果基础场景包含错误诱因 必须重新建立结构化场景合同并生成新的完整提示词

最终发送顺序固定为 当前帧目标 现实场景 可见物件 唯一动作 方向 文字 年代 正向风险替代 人物锁定 视觉风格 场景内容必须先于长篇风格描述

### 结构化模板

```json
{
  "prompt_contract_version": 2,
  "frames": [
    {
      "frame_id": "F01",
      "narrative_goal": "观众必须理解的意义",
      "literal_scene": "目标年代中可直接画出的单一现实场景",
      "visual_inventory": {
        "people": ["人物及数量"],
        "objects": ["物件及数量"],
        "environment": ["环境及年代"]
      },
      "primary_action": "唯一核心动作",
      "action_direction": "动作起点到终点",
      "approved_text": [],
      "historical_constraints": ["年代正向白名单"],
      "risk_flags": [],
      "model_misread_risk": "",
      "avoid_terms_in_prompt": [],
      "positive_replacements": [],
      "surface_contract": "所有可见表面的正向材质约束",
      "composition": "画幅 焦点和字幕安全区"
    }
  ]
}
```

## 旧版基础模板

```text
Use case: infographic-diagram plus historical scene
Asset type: native {aspect_ratio} static infographic frame for a Chinese history documentary
Frame: {frame_id}
Narrative meaning to communicate: {shot_voiceover_context}
Primary request: {single_visual_action}
Style preset: {warm-xuan-vox american-comic-vox knowledge-card or qibaishi-xieyi exactly one}
Style contract: {copy the full selected preset constraints above}
Composition: strict native {aspect_ratio} for {canvas_width}x{canvas_height} compose for that aspect ratio without cropping another layout main information and negative space follow the project contract
Required exact core text: {required_text}
Complete visible text-container plan: {text_plan}
Blank text containers allowed: no
Historical constraints: {period clothing weapons architecture fortification transport map scope}
Character IDs: {character_ids}
Character identity lock: {identity_prompt copied from characters/character-manifest.json}
Character reference rule: preserve only identity face age body silhouette hairstyle clothing silhouette and historically justified signature details; do not copy anchor pose framing background props lighting composition whitespace or brush marks
For knowledge-card every visible label frame note card legend data card map tag timeline tag and seal frame must contain its assigned text Decorative paper may be blank only when it has no text-like border Allow additional coherent historically accurate Chinese explanations only after review No garbled or pseudo text no watermark no signature no modern administrative boundary no modern object
```

## 人物母版纪律

- 先读取 [character-continuity.md](character-continuity.md)
- 重复且辨识度重要的人物使用 `strict` 单次出现或远景人物使用 `descriptive` 不为所有路人生成母版
- `strict` 角色必须有同一人物卡派生的脸部母版和全身母版 两张都经用户确认后才能用于场景图
- 逐帧写入 `character_ids` 生图脚本依据角色 ID 自动附加身份提示词和参考图 禁止手工另写一套冲突外貌
- 齐白石写意只锁身份线索 不锁姿态 构图 留白 笔墨 水痕和场景道具 防止人物像贴纸一样重复
- 母版参考图只传入当前镜头实际出现的严格角色 不把全部角色母版塞进每一帧

## 文字纪律

- `warm-xuan-vox` `american-comic-vox` 和 `qibaishi-xieyi` 从 `image_text` 中只提取引号内真正需要渲染的标签
- `qibaishi-xieyi` 默认无图内文字 只在内容不写出地名 数字或关系标签就无法准确表意时使用 `approved_text`
- `knowledge-card` 在生图前先为每帧规划主标题 核心标签和二至五组短讲解卡 并将所有可见文字容器写入 `text_plan`
- `knowledge-card` 验收时必须对照 `text_plan` 检查容器内容 且空白文字框数为零
- 位置词如 中央 左 右 上 下 旁 不得进入图像
- 前两种预设文字总量建议不超过 20 字
- `knowledge-card` 优先生成短标题 短标签 短句和图例 避免单张塞入长篇小字
- 只使用厚重木刻宋体或篆刻字形
- 数字使用中文形式如 前二〇二年 三十二万
- 生僻人名不强行写进图像 由口播和字幕承担
- 图内乱码 错字 残缺字 无意义字串和史实错误是发布阻断 不是风格瑕疵
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
5. `text_plan` 中每个文字容器是否有内容 空白文字框数是否为零
6. 未指定伪文字和水印
7. 底部字幕安全区
8. 前后镜风格一致性
9. 是否混入另一预设或未经批准的第五种风格
10. `qibaishi-xieyi` 是否真正从当前内容推导画面 而不是只保留水墨外观或复用旧物件
11. 同一 `character_id` 的年龄 脸型 发式 身形 服装轮廓和辨识特征是否连续 且未机械复制母版构图
