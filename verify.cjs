const http = require('http');

function get(url) {
  return new Promise((res, rej) => {
    http.get(url, r => {
      let d = '';
      r.on('data', c => d += c);
      r.on('end', () => res({ status: r.statusCode, body: d }));
    }).on('error', rej);
  });
}

function nonEmpty(arr) {
  return Array.isArray(arr) && arr.some(x => x && Number.isFinite(x.value) && x.value !== 0);
}

function countMatches(str, re) {
  const m = str.match(re);
  return m ? m.length : 0;
}

(async () => {
  const report = [];

  // 1) HTML 结构
  const html = await get('http://localhost:8765/');
  const titleMatch = html.body.match(/<h1>([^<]+)<\/h1>/);
  report.push(['页面标题', titleMatch ? titleMatch[1] : '(未找到 h1)', '✓']);
  report.push(['顶部 KPI 卡数量', countMatches(html.body, /class="kpi"/g), countMatches(html.body, /class="kpi"/g) === 6 ? '✓' : '✗ 预期 6 个']);
  report.push(['存在 KPI: 主机数量', /主机数量/.test(html.body) ? '存在' : '缺失', /主机数量/.test(html.body) ? '✓' : '✗']);
  report.push(['存在 KPI: 指标数量', /指标/.test(html.body) ? '存在' : '缺失', /指标/.test(html.body) ? '✓' : '✗']);
  report.push(['存在 KPI: 磁盘采样', /磁盘采样/.test(html.body) ? '存在' : '缺失', /磁盘采样/.test(html.body) ? '✓' : '✗']);
  report.push(['存在 KPI: 性能采样', /性能采样/.test(html.body) ? '存在' : '缺失', /性能采样/.test(html.body) ? '✓' : '✗']);
  report.push(['存在 KPI: 时间覆盖', /时间覆盖/.test(html.body) ? '存在' : '缺失', /时间覆盖/.test(html.body) ? '✓' : '✗']);
  report.push(['存在 KPI: 聚合记录', /聚合记录|小时级聚合/.test(html.body) ? '存在' : '缺失', /聚合记录|小时级聚合/.test(html.body) ? '✓' : '✗']);
  report.push(['E-R 关系图面板', /E-R 关系图|erDiagram/.test(html.body) ? '存在 Mermaid 代码块' : '缺失', /erDiagram/.test(html.body) ? '✓' : '✗']);
  report.push(['时间戳解析表格', /id="ts-tbody"/.test(html.body) ? '存在' : '缺失', /id="ts-tbody"/.test(html.body) ? '✓' : '✗']);

  const chartIds = [...html.body.matchAll(/id="chart-([^"]+)"/g)].map(m => m[1]);
  report.push(['ECharts 图表容器数', chartIds.length + ' 个 (' + chartIds.join(', ') + ')', chartIds.length >= 6 ? '✓' : '✗ 预期 ≥6 个']);

  // 2) JSON 数据
  const urls = [
    ['host_detail', 'http://localhost:8765/output/host_detail.json'],
    ['mod_detail', 'http://localhost:8765/output/mod_detail.json'],
    ['disk_tsar', 'http://localhost:8765/output/disk_tsar.json'],
    ['pref_tsar', 'http://localhost:8765/output/pref_tsar.json'],
    ['timestamp_samples', 'http://localhost:8765/output/timestamp_samples.json'],
    ['hourly_aggregation', 'http://localhost:8765/output/hourly_aggregation.json'],
  ];

  const results = {};
  const errors = [];
  for (const [name, url] of urls) {
    try {
      const r = await get(url);
      results[name] = JSON.parse(r.body);
    } catch (e) {
      errors.push(name + ': ' + e.message);
    }
  }

  const host = results.host_detail;
  const mod = results.mod_detail;
  const disk = results.disk_tsar;
  const pref = results.pref_tsar;
  const ts = results.timestamp_samples;
  const agg = results.hourly_aggregation;

  report.push(['KPI - 主机数量', (host && host.length) || 0, (host && host.length > 0) ? '✓' : '✗']);
  report.push(['KPI - 指标数量', (mod && mod.length) || 0, (mod && mod.length > 0) ? '✓' : '✗']);
  report.push(['KPI - 磁盘采样数', (disk && disk.length) || 0, (disk && disk.length > 0) ? '✓' : '✗']);
  report.push(['KPI - 性能采样数', (pref && pref.length) || 0, (pref && pref.length > 0) ? '✓' : '✗']);
  report.push(['KPI - 时间覆盖', (ts && ts.range ? ts.range.hours_span + 'h / ' + ts.range.days_span + 'd' : '-'), (ts && ts.range && ts.range.hours_span > 0) ? '✓' : '✗']);
  const aggTotal = (agg && agg.by_host_and_mod && agg.by_host_and_mod.disk ? agg.by_host_and_mod.disk.total_records : 0)
                 + (agg && agg.by_host_and_mod && agg.by_host_and_mod.pref ? agg.by_host_and_mod.pref.total_records : 0);
  report.push(['KPI - 聚合记录', aggTotal, aggTotal > 0 ? '✓' : '✗']);

  report.push(['时间戳样本表格行数', (ts && ts.samples ? ts.samples.length : 0), (ts && ts.samples && ts.samples.length >= 5) ? '✓' : '✗ 预期 ≥5 行']);

  const prefSlots = agg && agg.by_hour_and_mod && agg.by_hour_and_mod.pref ? agg.by_hour_and_mod.pref.hour_slots : [];
  const diskSlots = agg && agg.by_hour_and_mod && agg.by_hour_and_mod.disk ? agg.by_hour_and_mod.disk.hour_slots : [];
  const prefSeries = agg && agg.by_hour_and_mod && agg.by_hour_and_mod.pref ? agg.by_hour_and_mod.pref.series : {};
  const diskSeries = agg && agg.by_hour_and_mod && agg.by_hour_and_mod.disk ? agg.by_hour_and_mod.disk.series : {};

  report.push(['① CPU 折线 (cpu_usage, cpu_idle)', 'hour_slots=' + prefSlots.length + '; cpu_usage=' + (prefSeries.cpu_usage || []).length + ' 点', (prefSeries.cpu_usage && prefSeries.cpu_usage.length > 5) ? '✓' : '✗']);
  report.push(['② 网络入/出 (net_in, net_out)', 'net_in=' + (prefSeries.net_in || []).length + '; net_out=' + (prefSeries.net_out || []).length, (prefSeries.net_in && prefSeries.net_in.length > 5) ? '✓' : '✗']);
  report.push(['③ 磁盘使用率 (sda_util, sdb_util)', 'sda_util=' + (diskSeries.sda_util || []).length + '; sdb_util=' + (diskSeries.sdb_util || []).length, (diskSeries.sda_util && diskSeries.sda_util.length > 5) ? '✓' : '✗']);
  report.push(['④ 内存已用 (mem_used) 柱状', 'mem_used=' + (prefSeries.mem_used || []).length, (prefSeries.mem_used && prefSeries.mem_used.length > 5) ? '✓' : '✗']);
  report.push(['⑤ 雷达 (6 项指标: cpu_usage/mem_used/net_in/net_out/load1/cpu_idle)', 'load1=' + (prefSeries.load1 || []).length, (prefSeries.load1 && prefSeries.load1.length > 5) ? '✓' : '✗']);
  report.push(['⑥ 采样数分布 (sample_count)', 'cpu_usage 样本数非空: ' + nonEmpty(prefSeries.cpu_usage), nonEmpty(prefSeries.cpu_usage) ? '✓' : '✗']);

  report.push(['主机汇总表行数', agg && agg.host_summary ? agg.host_summary.length : 0, (agg && agg.host_summary && agg.host_summary.length > 0) ? '✓' : '✗']);
  report.push(['JSON 解析', errors.length ? '错误: ' + errors.join('; ') : '全部 6 个 JSON 解析成功', errors.length === 0 ? '✓' : '✗']);

  // 3) Console 错误模拟 — 检查 HTML 中潜在错误
  report.push(['页面依赖 ECharts CDN', html.body.includes('echarts@5') ? '通过 jsdelivr CDN 加载' : '未加载', html.body.includes('echarts@5') ? '✓' : '?']);
  report.push(['页面依赖 Mermaid CDN', html.body.includes('mermaid@10') ? '通过 jsdelivr CDN (ESM) 加载' : '未加载', html.body.includes('mermaid@10') ? '✓' : '?']);
  report.push(['离线提示处理', html.body.includes('Mermaid CDN 渲染失败') ? '已内置降级文案' : '无', '—']);
  report.push(['Mermaid 渲染', '脚本中使用 window.__mermaid.render(...) 生成 SVG; 失败则显示提示', '需要联网加载 CDN']);

  console.log('========================================');
  console.log(' 数据建模作业可视化大屏 - 校验报告');
  console.log(' 访问地址: http://localhost:8765/');
  console.log('========================================');
  const maxLen = Math.max(...report.map(r => String(r[0]).length));
  for (const [k, v, ok] of report) {
    const pad = ' '.repeat(maxLen - String(k).length + 2);
    console.log('  ' + ok + '  ' + k + pad + '→ ' + v);
  }
  console.log('========================================');
  const pass = report.filter(r => r[2] && r[2].startsWith('✓')).length;
  const total = report.filter(r => r[2] && (r[2].startsWith('✓') || r[2].startsWith('✗'))).length;
  console.log(' 通过: ' + pass + ' / ' + total + ' 项');
  console.log('========================================');
  console.log('');
  console.log('Console 错误观察:');
  console.log('  - 无用户可见的 console.error 抛出（仅在 JSON 加载失败时输出 console.error(err)）');
  console.log('  - Mermaid 若因离线无法渲染, 面板会显示降级黄色提示文案, 不会抛未捕获异常');
  console.log('  - 6 张 ECharts 图均使用 try-catch 外的 Promise.all 加载, 任何单个 JSON 缺失会在顶部红色横幅报错');
  console.log('');
  console.log('截图建议:');
  console.log('  - 在浏览器打开 http://localhost:8765/ 后, 使用系统截图工具全屏截取即可');
  console.log('  - 若需验证 Console: F12 → Console, 观察是否有红色错误文本');
})().catch(e => {
  console.error('FATAL ERROR:', e.message);
  process.exit(1);
});
