// ============================
// 词云页 - JS
// ============================

// 20 色调色板，每个学科按名称哈希取固定颜色
const DISCIPLINE_COLORS = [
    "#4a90e2", "#50c7a0", "#f5a623", "#d0648a",
    "#7b5ea7", "#3db9af", "#e87e04", "#5b8dee",
    "#c23531", "#2f4554", "#61a0a0", "#946b4d",
    "#8cb369", "#d499b9", "#9f8abe", "#e0a73e",
    "#6c8cd5", "#7fb5b5", "#cf7f7f", "#a0c4a0"
];

function hashIndex(name) {
    let h = 0;
    for (let i = 0; i < name.length; i++) {
        h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
    }
    return Math.abs(h) % DISCIPLINE_COLORS.length;
}

// 将树数据展平为词云格式：一级 + 二级学科 name → paper_count
function flattenToWordCloud(nodes) {
    const words = [];
    nodes.forEach(l1 => {
        // 一级学科
        words.push({
            name: l1.name,
            value: l1.paper_count,
            itemStyle: { color: DISCIPLINE_COLORS[hashIndex(l1.name)] }
        });
        // 二级学科
        (l1.children || []).forEach(l2 => {
            words.push({
                name: l2.name,
                value: l2.paper_count,
                itemStyle: { color: DISCIPLINE_COLORS[hashIndex(l2.name)] }
            });
        });
    });
    return words;
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
    const savedPath = sessionStorage.getItem("last_path_wordcloud");
    if (savedPath) pathInput.value = savedPath;

    // 初始化图表
    chart = echarts.init(document.getElementById("chart"));
    window.addEventListener("resize", () => chart.resize());

    loadBtn.addEventListener("click", loadWordCloud);
    pathInput.addEventListener("keypress", (e) => { if (e.key === "Enter") loadWordCloud(); });

    async function loadWordCloud() {
        const path = pathInput.value.trim();
        if (!path) { showError("请输入目录路径"); return; }
        loadBtn.disabled = true;
        loadBtn.textContent = "加载中...";
        hideError();
        statsBar.style.display = "none";

        try {
            const data = await fetchSunburst(path);
            if (!data || data.length === 0) { showError("目录为空或路径不存在"); return; }

            sessionStorage.setItem("last_path_wordcloud", path);

            const words = flattenToWordCloud(data);
            const totalPapers = data.reduce((sum, n) => sum + (n.paper_count || 0), 0);

            const option = {
                tooltip: {
                    show: true,
                    formatter: params => `${params.name}<br/>论文数：${params.value}`
                },
                series: [{
                    type: "wordCloud",
                    shape: "circle",
                    left: "center",
                    top: "center",
                    width: "90%",
                    height: "90%",
                    sizeRange: [16, 72],
                    rotationRange: [-30, 30],
                    rotationStep: 15,
                    gridSize: 8,
                    drawOutOfBound: false,
                    textStyle: {
                        fontFamily: "PingFang SC, Microsoft YaHei, sans-serif",
                        fontWeight: "bold"
                                       },
                    emphasis: {
                        textStyle: {
                            shadowBlur: 10,
                            shadowColor: "#333"
                        }
                    },
                    data: words
                }]
            };

            // 隐藏占位提示
            const ph = document.querySelector("#chart .chart-placeholder");
            if (ph) ph.style.display = "none";

            chart.setOption(option, true);

            const l2Count = data.reduce((sum, n) => sum + (n.children?.length || 0), 0);
            statsText.textContent = `共 ${data.length} 个一级学科，${l2Count} 个二级学科，${totalPapers} 篇论文`;
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
