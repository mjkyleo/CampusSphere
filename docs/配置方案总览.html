<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CampusSphere 配置化方案总览</title>
<style>
  :root{
    --text:#1A1B1C; --sub:#6B7280; --bg:#F4F3EE; --card:#FFFFFF;
    --border:#E4E3DD; --accent:#2F6BFF; --accent-bg:rgba(47,107,255,0.08);
    --ok:#1F8A4C; --ok-bg:#E7F5EC; --warn:#B7791F; --warn-bg:#FBF1DE;
    --bad:#C0392B; --bad-bg:#F9E9E7; --add:#8A2BE2; --add-bg:#F1E7FB;
  }
  *{box-sizing:border-box; margin:0; padding:0;}
  body{background:var(--bg); color:var(--text); font-family:'PingFang SC','Microsoft YaHei',system-ui,sans-serif; padding:16px; line-height:1.5;}
  h1{font-size:17px; font-weight:600; margin-bottom:2px;}
  .sub{font-size:12px; color:var(--sub); margin-bottom:16px;}
  .card{background:var(--card); border:1px solid var(--border); border-radius:14px; padding:16px; margin-bottom:16px;}
  .card h2{font-size:14px; font-weight:600; margin-bottom:12px; display:flex; align-items:center; gap:6px;}
  .step-num{display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; border-radius:50%; background:var(--accent); color:#fff; font-size:12px; flex:0 0 auto;}
  .flow{display:flex; flex-wrap:wrap; align-items:center; gap:8px; justify-content:center;}
  .node{padding:10px 12px; border-radius:10px; background:var(--accent-bg); border:1px solid var(--accent); font-size:13px; text-align:center; min-width:120px;}
  .node small{display:block; color:var(--sub); font-size:11px; margin-top:2px;}
  .node.file{background:#FFF8E6; border-color:#E0B84C;}
  .node.db{background:#E7F0FF; border-color:#7AA7FF;}
  .node.api{background:#E7F5EC; border-color:#62B87E;}
  .node.fe{background:#F5EDFF; border-color:#A977E0;}
  .arrow{color:var(--sub); font-size:16px; font-weight:700;}
  table{width:100%; border-collapse:collapse; font-size:13px;}
  th,td{border-bottom:1px solid var(--border); padding:7px 6px; text-align:left; vertical-align:top;}
  th{font-size:12px; color:var(--sub); font-weight:500; background:#FAFAF7;}
  .pill{display:inline-block; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:500; white-space:nowrap;}
  .ok{background:var(--ok-bg); color:var(--ok);}
  .warn{background:var(--warn-bg); color:var(--warn);}
  .bad{background:var(--bad-bg); color:var(--bad);}
  .add{background:var(--add-bg); color:var(--add);}
  .tag{font-size:11px; color:var(--sub);}
  .tree{font-size:13px;}
  .tree .l1{font-weight:600; padding:4px 0;}
  .tree .l2{display:flex; flex-wrap:wrap; gap:4px; padding:2px 0 6px 0;}
  .chip{background:#F2F4F7; border:1px solid var(--border); border-radius:16px; padding:2px 9px; font-size:11px; color:#3A3F47;}
  .tree .l1 .cap{display:inline-block; min-width:110px; color:#fff; border-radius:6px; padding:2px 8px; font-size:12px; text-align:center;}
  .legend{display:flex; flex-wrap:wrap; gap:12px; font-size:12px; color:var(--sub); margin-top:8px;}
  .legend span{display:inline-flex; align-items:center; gap:4px;}
  .dot{width:10px; height:10px; border-radius:50%; display:inline-block;}
  .lockflow{display:flex; flex-direction:column; gap:8px; font-size:13px;}
  .step{display:flex; gap:10px; align-items:flex-start;}
  .step .s{flex:0 0 auto; width:22px; height:22px; border-radius:6px; background:var(--bad-bg); color:var(--bad); font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center;}
  .step.done .s{background:var(--ok-bg); color:var(--ok);}
  .step b{font-weight:600;}
  .note{font-size:11px; color:var(--sub); margin-top:6px;}
</style>
</head>
<body>
  <h1>CampusSphere · 配置化改造方案总览</h1>
  <div class="sub">依据已核查代码与运行中服务（前端 5173 → 后端 8000）；食堂数据已按武大官方介绍核实（3 类 22 个）· 院系清单以官方为准可微调 · 方案待确认</div>

  <!-- 1 配置链路 -->
  <div class="card">
    <h2><span class="step-num">1</span> 分类/院系/食堂统一为「四层热更新」配置链路</h2>
    <div class="flow">
      <div class="node file">config/school.yaml<small>默认值（单校配置）</small></div>
      <div class="arrow">→</div>
      <div class="node db">AppConfig 表（DB）<small>管理后台 PUT 覆盖，无需重启</small></div>
      <div class="arrow">→</div>
      <div class="node api">公开 GET 端点<small>/api/{items,courses,jobs,shares,teammates,canteens}/...</small></div>
      <div class="arrow">→</div>
      <div class="node fe">前端动态拉取<small>保留 FALLBACK 兜底</small></div>
    </div>
    <div class="note">已就位：二手分类、课程院系；待补齐：兼职/分享/搭子分类、食堂学部/学期。</div>
  </div>

  <!-- 2 六模块对照 -->
  <div class="card">
    <h2><span class="step-num">2</span> 六类功能分类管理：现状 vs 目标</h2>
    <table>
      <tr><th>功能</th><th>现状来源</th><th>是否热更新</th><th>目标</th></tr>
      <tr><td>二手（分类）</td><td class="tag">school.yaml + 管理后台 + GET</td><td><span class="pill ok">✅ 已支持</span></td><td class="tag">保持</td></tr>
      <tr><td>课程（院系）</td><td class="tag">school.yaml + 管理后台 + GET</td><td><span class="pill ok">✅ 已支持</span></td><td class="tag">按学部两级组织（防拥堵）</td></tr>
      <tr><td>兼职（分类）</td><td class="tag">前端写死数组</td><td><span class="pill bad">❌ 写死</span></td><td><span class="pill add">→ 四层配置化</span></td></tr>
      <tr><td>分享（分类）</td><td class="tag">前端写死数组</td><td><span class="pill bad">❌ 写死</span></td><td><span class="pill add">→ 四层配置化</span></td></tr>
      <tr><td>搭子（分类）</td><td class="tag">前端写死数组</td><td><span class="pill bad">❌ 写死</span></td><td><span class="pill add">→ 四层配置化</span></td></tr>
      <tr><td>食堂（学部/餐饮区/类型）</td><td class="tag">无（表空、缺维度字段）</td><td><span class="pill warn">— 待新增</span></td><td><span class="pill add">新增 campus/zone/type/semester + seed</span></td></tr>
    </table>
    <div class="legend">
      <span><span class="dot" style="background:var(--ok)"></span>已达标</span>
      <span><span class="dot" style="background:var(--bad)"></span>需改造</span>
      <span><span class="dot" style="background:var(--add)"></span>本次新增</span>
    </div>
  </div>

  <!-- 3 层级组织 -->
  <div class="card">
    <h2><span class="step-num">3</span> 食堂 / 课程院系 按「学部」两级组织，避免拥挤</h2>
    <div class="tree">
      <div class="l1"><span class="cap" style="background:#2F6BFF">食堂 · 4 学部 / 9 餐饮区 / 3 类 22 个</span> 梅园·桂园·枫园(文理) ｜ 湖滨·工学部·田园(工学) ｜ 信息学部·星园(信息) ｜ 杏园(医学)</div>
      <div class="l2">
        <span class="chip">学生大伙食堂</span><span class="chip">风味食堂</span><span class="chip">教工食堂</span>
      </div>
      <div class="l2">
        <span class="chip">文理学部</span><span class="chip">工学部</span><span class="chip">信息学部</span><span class="chip">医学部</span>
      </div>
      <div class="l1" style="margin-top:8px;"><span class="cap" style="background:#8A2BE2">课程院系 · 6 学部组</span> 文学院·历史·哲学·外语 ｜ 经管·法学·信息管理 ｜ 数学·物理·化学·生科 ｜ 水利·电气·土木·测绘 ｜ 计算机·软件·网安·电信·AI ｜ 基础医学·口腔·临床</div>
      <div class="l2">
        <span class="chip">人文科学</span><span class="chip">社会科学</span><span class="chip">理学</span><span class="chip">工学</span><span class="chip">信息科学</span><span class="chip">医学</span><span class="chip">跨学科/通识</span>
      </div>
    </div>
    <div class="note">食堂（已定稿）：杏园按楼层拆 3 条 Canteen、梅园 CBD 以「商业街」标签收录；前端：一级学部 Tab（6~7 个不溢出）+ 二级院系 chips / 折叠。</div>
  </div>

  <!-- 4 并发 -->
  <div class="card">
    <h2><span class="step-num">4</span> 二手交易并发加固：原子抢占 + DB 兜底</h2>
    <div class="lockflow">
      <div class="step done"><span class="s">✓</span><div><b>条件 UPDATE 抢占</b>：<code>UPDATE items SET status=RESERVED WHERE id=? AND status=ON_SALE</code>，受影响行数=1 才建会话，否则 409 —— 同一物品同时只有一个活跃交易</div></div>
      <div class="step done"><span class="s">✓</span><div><b>部分唯一索引兜底</b>：<code>UNIQUE(item_id) WHERE status=ACTIVE</code>，另加 <code>(item_id,buyer_id)</code> 防重复点击</div></div>
      <div class="step done"><span class="s">✓</span><div><b>状态变更统一走条件 UPDATE</b>：改价/上下架/成交全部带旧状态条件，事务内提交</div></div>
      <div class="step"><span class="s">!</span><div>现状风险：<code>create_trade_session</code> 为「先查后插」无锁，并发下可同物多会话（当前 4 会话分属不同物品，未暴露）</div></div>
    </div>
  </div>
</body>
</html>
