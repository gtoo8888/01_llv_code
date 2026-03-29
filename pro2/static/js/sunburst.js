// ============================
// 旭日图页 - JS
// ============================

// 20 色调色板，每个二级学科按名称哈希取固定颜色
const DISCIPLINE_COLORS = [
    "#4a90e2", "#50c7a0", "#f5a623", "#d0648a",
    "#7b5ea7", "#3db9af", "#e87e04", "#5b8dee",
    "#c23531", "#2f4554", "#61a0a0", "#946b4d",
    "#8cb369", "#d499b9", "#9f8abe", "#e0a73e",
    "#6c8cd5", "#7fb5b5", "#cf7f7f", "#a0c4a0"
];

// 字符串哈希 → 返回 [0, 19] 的整数索引
function hashIndex(name) {
    let h = 0;
    for (let i = 0; i < name.length; i++) {
        h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
    }
    return Math.abs(h) % DISCIPLINE_COLORS.length;
}

// 获取某个二级学科的颜色（固定）
function l2Color(name) {
    return DISCIPLINE_COLORS[hashIndex(name)];
}

// 颜色变暗（opacity 降低模拟暗色）
function withOpacity(hex, alpha) {
    const num = parseInt(hex.replace("#", ""), 16);
    const R = num >> 16;
    const G = (num >> 8) & 0xff;
    const B = num & 0xff;
    return `rgba(${R},${G},${B},${alpha})`;
}

// 转为 ECharts 格式，depth=0=一级，depth=1=二级，depth=2=三级
function toSunburstData(node, depth, parentL2Color) {
    if (depth === 1) {
        // 二级：取自己的固定颜色
        const color = l2Color(node.name);
        return {
            name: node.name,
            value: node.paper_count,
            itemStyle: { color: color },
            children: (node.children || []).map(c => toSunburstData(c, 2, color))
        };
    } else if (depth === 2) {
        // 三级：继承父二级颜色，透明度区分
        return {
            name: node.name,
            value: node.paper_count,
            itemStyle: { color: withOpacity(parentL2Color, 0.7) },
            children: []
        };
    } else {
        // depth=0 一级：特殊处理，等全部转换完再补充颜色
        return {
            name: node.name,
            value: node.paper_count,
            children: (node.children || []).map(c => toSunburstData(c, 1, null))
        };
    }
}

// 一级学科颜色 = 其二级颜色平均值（简单取第一个二级颜色）
function resolveL1Colors(nodes) {
    return nodes.map(node => {
        const l2Colors = [];
        function collectL2(n) {
            if (n.depth === 1) l2Colors.push(l2Color(n.name));
            (n.children || []).forEach(collectL2);
        }
        node.children = node.children || [];
        collectL2({ children: node.children, depth: 0 });
        const color = l2Colors[0] || DISCIPLINE_COLORS[0];
        return {
            ...node,
            itemStyle: { color: color },
            children: node.children
        };
    });
}

// 统计目录数
function countDirs(nodes) {
    let count = 0;
    nodes.forEach(n => {
        count += 1;
        if (n.children) count += countDirs(n.children);
    });
    return count;
}

// ----- 初始化 -----
let chart = null;

function init() {
    const pathInput = document.getElementById("path_input");
    const loadBtn = document.getElementById("load_btn");
    const errorMsg = document.getElementById("error_msg");
    const statsBar = document.getElementById("stats_bar");
    const statsText = document.getElementById("stats_text");

    // 恢复上次路径
    const savedPath = sessionStorage.getItem("last_path_sunburst");
    if (savedPath) pathInput.value = savedPath;

    // 初始化图表
    chart = echarts.init(document.getElementById("chart"));
    window.addEventListener("resize", () => chart.resize());

    loadBtn.addEventListener("click", loadSunburst);
    pathInput.addEventListener("keypress", (e) => { if (e.key === "Enter") loadSunburst(); });

    // 初始占位提示
    const placeholder = document.createElement("div");
    placeholder.className = "chart-placeholder";
    placeholder.textContent = "点击「加载」按钮生成旭日图";
    placeholder.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:15px;pointer-events:none;z-index:1;";
    document.getElementById("chart").style.position = "relative";
    document.getElementById("chart").appendChild(placeholder);

    async function loadSunburst() {
        const path = pathInput.value.trim();
        if (!path) { showError("请输入目录路径"); return; }
        loadBtn.disabled = true;
        loadBtn.textContent = "加载中...";
        hideError();
        statsBar.style.display = "none";

        try {
            const data = await fetchSunburst(path);
            if (!data || data.length === 0) { showError("目录为空或路径不存在"); return; }

            sessionStorage.setItem("last_path_sunburst", path);

            // 转换为带颜色的旭日图数据
            // 先按层级转换：depth=0 一级, depth=1 二级, depth=2 三级
            let treeData = data.map(node => toSunburstData(node, 0, null));
            // 一级学科颜色取其第一个二级学科的颜色
            treeData.forEach(node => {
                if (node.children && node.children.length > 0) {
                    const firstL2Color = node.children[0].itemStyle?.color || DISCIPLINE_COLORS[0];
                    node.itemStyle = { color: firstL2Color };
                } else {
                    node.itemStyle = { color: DISCIPLINE_COLORS[0] };
                }
            });

            const option = {
                tooltip: {
                    trigger: "item",
                    formatter: params => `${params.name}<br/>论文数：${params.value}`
                },
                series: {
                    type: "sunburst",
                    data: treeData,
                    radius: ["5%", "90%"],
                    sort: null,
                    levels: [
                        {},
                        { r0: "5%", r: "30%", label: { rotate: "tangential", fontSize: 12, fontWeight: 600, color: "#fff" } },
                        { r0: "30%", r: "60%", label: { align: "right", fontSize: 11, color: "#fff" } },
                        { r0: "60%", r: "90%", label: { align: "right", fontSize: 10, color: "#fff" } }
                    ],
                    itemStyle: { borderRadius: 4, borderWidth: 2, borderColor: "#fff" },
                    label: { color: "#fff", textBorderColor: "rgba(0,0,0,0.3)", textBorderWidth: 1 }
                }
            };

            const ph = document.querySelector("#chart .chart-placeholder");
            if (ph) ph.style.display = "none";

            chart.setOption(option, true);

            const td = countDirs(data);
            const totalPapers = data.reduce((sum, n) => sum + (n.paper_count || 0), 0);
            statsText.textContent = `共 ${td} 个学科，${data.length} 个一级学科，${totalPapers} 篇论文`;
            statsBar.style.display = "block";

        } catch (err) {
            showError(err.message);
        } finally {
            loadBtn.disabled = false;
            loadBtn.textContent = "加载";
        }
    }

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = "block";
    }

    function hideError() {
        errorMsg.style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", init);
