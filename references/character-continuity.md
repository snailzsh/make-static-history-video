# 人物连续性合同

## 目的

人物一致性不是靠每帧临时重写描述实现 而是用稳定角色 ID 人物卡 两类母版 逐帧引用和批量前校验共同约束

人物外貌没有史料时 人物卡是生产设计 不是历史肖像 所有具体脸型 年龄和辨识特征都必须明确这一边界

## 连续性分级

- `strict` 主角或跨两个以上关键画面反复出现且需要被观众认出的角色
- `descriptive` 单次出现 远景 群像或无需辨认身份的角色 只用文字人物卡
- `skip` 纯剪影 无脸人群或不出现人物的项目

不为所有路人生成母版 先按分镜统计出场次数和景别 再决定级别

## 固定产物

`characters/character-manifest.json` 是人物身份唯一真实源

```json
{
  "schema_version": 1,
  "style_preset": "qibaishi-xieyi",
  "characters": [
    {
      "character_id": "C01",
      "name": "人物名",
      "continuity": "strict",
      "depiction_basis": "production design not a verified historical portrait",
      "identity_prompt": "每次出现都必须保持一致的年龄 脸型 身形 发式 服装轮廓和辨识特征",
      "mutable_by_scene": ["姿态", "表情", "视角", "构图", "留白", "笔墨", "场景道具"],
      "anchors": {
        "face": "characters/anchors/C01-face.png",
        "full_body": "characters/anchors/C01-full-body.png"
      },
      "status": "draft"
    }
  ]
}
```

状态只允许 `draft` `generated` `confirmed` `rejected` `skipped`

## 母版生成和确认

1. 脸部母版用中性三分之四视角 清楚呈现脸型 五官 年龄 发式和面部毛发 不带剧情动作
2. 全身母版用自然站姿 清楚呈现身形 服装层级 袖口 下摆 腰带 鞋履和可核定的身份物件
3. 两张母版来自同一人物卡 不使用多人物宫格 不加入会被后续误继承的场景背景
4. 用户逐个确认严格角色 两张母版任一未确认时角色状态不能设为 `confirmed`
5. 被拒绝的母版保留在 rejected 记录中 只重生对应角色和对应母版

## 齐白石写意的软锁规则

锁定：角色 ID 年龄区间 脸型主要轮廓 身形比例 发式 面部毛发 服装轮廓与稳定色彩 史实允许的辨识特征

放开：姿态 表情 视角 景别 动作 场景道具 物体距离 留白形状 笔锋压力 墨色浓淡 水痕和构图

参考图只提供身份依据 不得复制母版的姿势 机位 背景 光线 留白或笔墨布局 这样既减少换脸和换装 也不破坏 `qibaishi-xieyi` 的内容生长式构图

## 逐帧继承

- `storyboards/frame-manifest.json` 和 `prompts/frame-prompts.json` 都写入 `character_ids`
- 生图脚本按角色 ID 从人物卡附加 `identity_prompt` 并把当前镜头严格角色的脸部与全身母版加入 `generation_reference_images`
- 一个镜头只传入实际出现角色的母版 不传无关角色
- 同一角色不得在逐帧提示词中重新定义相冲突的年龄 发式 服装或体型

## 阻断与 QA

- 严格角色未确认两张母版时 禁止批量生成场景图
- 未知角色 ID 母版文件缺失或人物卡风格与项目风格不一致时 生图前停止
- 原图审查逐项比对年龄 脸型 发式 面部毛发 身形和服装轮廓
- 身份漂移只重生当前帧 保留失败图和 repair 日志 不用文字说明把不同人物解释成同一人
- 齐白石写意允许线条和墨色自然变化 但不能把年龄 发式 身形或服装轮廓变化误判为风格自由
