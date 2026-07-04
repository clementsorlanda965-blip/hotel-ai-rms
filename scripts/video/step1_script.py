# =============================================
# step1_script.py - 视频流水线第1步：剧本生成
# 生成10个场景的完整分镜脚本 (output/script.json)
# 包含: 视觉描述、旁白、字幕、情绪标签、关键词
# =============================================
import json, os
os.makedirs("output", exist_ok=True)

# 10个场景分镜脚本 — 带关键词标记
SCRIPT_SCENES = [
    {"id": 0, "start": 0.0, "end": 5.0,
     "visual": "午门雪景 青石板血迹 暗红天空",
     "narration": "就一句话的事儿，命没了。一个正五品的钦天监监正，说了几句大实话，就活活被打死。可你要是觉得周云逸是死于直谏——那你只看了个皮毛。",
     "subtitle": "一句话，命没了",
     "emotion": "hook",
     "keywords": ["命没了", "活活被打死"]},

    {"id": 1, "start": 5.0, "end": 9.5,
     "visual": "紫禁城雪夜 万寿宫大火 浓烟",
     "narration": "往深了刨，他踩的，是皇权最不能说出口的那个秘密。嘉靖三十九年冬天，北境好几个省一滴雪都没下。在信奉天人感应的年代，不下雪就是老天在扇皇帝的耳光。",
     "subtitle": "不能说的秘密",
     "emotion": "悬念",
     "keywords": ["不能说出口的秘密", "扇皇帝的耳光"]},

    {"id": 2, "start": 9.5, "end": 14.5,
     "visual": "嘉靖道观炼丹 香烟缭绕",
     "narration": "刚好这时候，万寿宫又烧了。两件事一碰，民间炸了锅，矛头全指向那个二十多年不上朝的嘉靖。嘉靖急了，把钦天监监正周云逸叫来。他要的是台阶——让周云逸告诉天下人：不下雪是自然规律，跟皇帝没关系。",
     "subtitle": "他要的是台阶",
     "emotion": "冲突",
     "keywords": ["台阶"]},

    {"id": 3, "start": 14.5, "end": 19.0,
     "visual": "周云逸朝堂陈词 慷慨激昂",
     "narration": "但周云逸偏不。他一开口就是王炸：朝廷开支无度，官府贪墨横行，民不聊生，天怒人怨！十六个字。每个字都像刀子。直接把天灾的锅，甩到了嘉靖和整个朝堂脸上。",
     "subtitle": "十六个字，个个是刀",
     "emotion": "亢奋",
     "keywords": ["十六个字", "每个字都像刀子"]},

    {"id": 4, "start": 19.0, "end": 23.5,
     "visual": "冯保行刑 午门 廷杖 鲜血",
     "narration": "行刑的是东厂提督冯保。他当场逼问：谁指使你的？周云逸到死都没松口。午门外，廷杖致死。你知道他这番话背后站的是谁吗？裕王。",
     "subtitle": "到死都没松口",
     "emotion": "冲突",
     "keywords": ["到死都没松口", "廷杖致死"]},

    {"id": 5, "start": 23.5, "end": 28.5,
     "visual": "裕王府 清流密谈 暗灯",
     "narration": "裕王是清流派的核心。周云逸的死，说到底是清流和严党第一次正面交锋的牺牲品。原著作者刘和平把这段戏叫做整部剧的蝎子尾——很短，但很毒。",
     "subtitle": "清流和严党的牺牲品",
     "emotion": "顿悟",
     "keywords": ["牺牲品", "蝎子尾"]},

    {"id": 6, "start": 28.5, "end": 33.5,
     "visual": "嘉靖独坐龙椅 帘幕低垂",
     "narration": "我跟你讲，周云逸真不是莽夫。他是钦天监的人，说白了就是皇权的扩音器。嘉靖让你来，是让你给他圆场的。可周云逸偏不圆。",
     "subtitle": "皇权的扩音器",
     "emotion": "顿悟",
     "keywords": ["皇权的扩音器"]},

    {"id": 7, "start": 33.5, "end": 38.5,
     "visual": "嘉靖朱笔批奏折 红字刺目",
     "narration": "你以为嘉靖被冒犯了、恼羞成怒杀人？不是的。他是在用周云逸的血警告所有人：天，只能是我嘉靖的天；对错，只能由我一人定。",
     "subtitle": "天，只能是我嘉靖的天",
     "emotion": "梗慨",
     "keywords": ["我嘉靖的天"]},

    {"id": 8, "start": 38.5, "end": 43.5,
     "visual": "宫墙阴影 青石板血迹 孤影",
     "narration": "周云逸的刚直，是风骨，可也是傻。他以为凭一己之力能把装睡的人叫醒。可他不知道——在一个只看权力不看真相的体系里，真相不值钱。",
     "subtitle": "真相不值钱",
     "emotion": "共鸣",
     "keywords": ["风骨", "真相不值钱"]},

    {"id": 9, "start": 43.5, "end": 50.0,
     "visual": "雪中紫禁城全景 黎明天光",
     "narration": "周云逸的血渗进了午门的青石板缝，像大明王朝崩塌前的第一粒雪。这场雪，马上就要掀起一场掀翻整个朝堂的暴风雪——天谴的流言还没熄，国库的窟窿已经烫手了。",
     "subtitle": "大明崩塌前的第一粒雪",
     "emotion": "激励",
     "keywords": ["第一粒雪", "暴风雪"]}
]

with open("output/script.json", "w", encoding="utf-8") as f:
    json.dump(SCRIPT_SCENES, f, ensure_ascii=False, indent=2)

total_dur = SCRIPT_SCENES[-1]["end"]
total_chars = sum(len(s["narration"]) for s in SCRIPT_SCENES)
print(f"[1/6] 剧本已生成: {len(SCRIPT_SCENES)} 镜头, {total_dur:.0f}秒, {total_chars}字")
print(f"   语速预估: {total_chars/total_dur:.1f} 字/秒")
print(f"   关键词标记: {sum(len(s['keywords']) for s in SCRIPT_SCENES)} 个")
