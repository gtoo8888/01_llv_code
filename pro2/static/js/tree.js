// ============================
// 目录树页 - JS
// ============================

// ----- 数据 -----
let treeRawData = []; // 原始目录树数据（搜索时需要完整结构）

// ----- 通用工具 -----
function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function countDirs(nodes) {
    let count = 0;
    nodes.forEach(n => {
        count += 1;
        if (n.children) count += countDirs(n.children);
    });
    return count;
}

function countFiles(nodes) {
    let count = 0;
    nodes.forEach(n => {
        if (!n.children || n.children.length === 0) count += 1;
        if (n.children) count += countFiles(n.children);
    });
    return count;
}

// ----- 树图渲染 -----
function countLeaves(node) {
    if (!node.children || node.children.length === 0) return 1;
    return node.children.reduce((sum, c) => sum + countLeaves(c), 0);
}

function countDirsInNode(node) {
    if (!node.children || node.children.length === 0) return 0;
    let count = node.children.length;
    node.children.forEach(c => { count += countDirsInNode(c); });
    return count;
}

function isFile(node) {
    return !node.children || node.children.length === 0;
}

function buildNodeHTML(node, depth = 0) {
    const fileNode = isFile(node);
    const hasChildren = node.children && node.children.length > 0;
    const leafCount = hasChildren ? countLeaves(node) : 0;
    const dirCount = hasChildren ? countDirsInNode(node) : 0;
    const nodeClass = fileNode ? "tree-node file" : "tree-node dir";

    let html = `<div class="${nodeClass}" data-depth="${depth}">`;
    html += `<div class="tree-node-content">`;
    html += `<span class="tree-arrow${hasChildren ? " open" : " empty"}">▶</span>`;
    html += `<span class="tree-icon">${fileNode ? "📄" : "📁"}</span>`;
    html += `<span class="tree-name">${escapeHTML(node.name)}</span>`;
    if (hasChildren) {
        html += `<span class="tree-count">${dirCount} 目录, ${leafCount} 文件</span>`;
    }
    html += `</div>`;

    if (hasChildren) {
        html += `<div class="tree-children" style="max-height: 50000px;">`;
        node.children.forEach(child => { html += buildNodeHTML(child, depth + 1); });
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

// 递归标记匹配的节点（保留匹配节点及其所有祖先）
function markMatches(node, keyword) {
    const lowerKeyword = keyword.toLowerCase();
    const nameMatches = node.name.toLowerCase().includes(lowerKeyword);
    let childMatched = false;

    if (node.children) {
        node.children.forEach(child => {
            if (markMatches(child, keyword)) {
                childMatched = true;
            }
        });
    }

    if (nameMatches || childMatched) {
        node._matched = true;
    }

    return nameMatches || childMatched;
}

// 过滤：移除没有 _matched 标记的叶子节点
function pruneUnmatched(node) {
    if (!node.children || node.children.length === 0) {
        return node._matched ? node : null;
    }

    node.children = node.children
        .map(child => pruneUnmatched(child))
        .filter(child => child !== null);

    if (node._matched || node.children.length > 0) {
        node._matched = true;
        return node;
    }
    return null;
}

function renderTree(data) {
    const wrapper = document.getElementById("tree_wrapper");
    if (!data || data.length === 0) {
        wrapper.innerHTML = '<div class="tree-placeholder">目录为空</div>';
        return;
    }
    let html = "";
    data.forEach(node => { html += buildNodeHTML(node, 0); });
    wrapper.innerHTML = html;

    // 文件夹展开/折叠
    wrapper.querySelectorAll(".tree-node.dir > .tree-node-content").forEach(el => {
        el.addEventListener("click", function() {
            const nodeEl = this.closest(".tree-node");
            const arrow = this.querySelector(".tree-arrow");
            const children = nodeEl.querySelector(".tree-children");
            if (!children) return;
            if (arrow.classList.contains("open")) {
                arrow.classList.remove("open");
                children.style.maxHeight = "0px";
            } else {
                arrow.classList.add("open");
                children.style.maxHeight = "50000px";
            }
        });
    });

    // 文件节点选中效果
    wrapper.querySelectorAll(".tree-node.file > .tree-node-content").forEach(el => {
        el.addEventListener("click", function() {
            wrapper.querySelectorAll(".tree-node-content.active").forEach(a => a.classList.remove("active"));
            this.classList.add("active");
        });
    });
}

// ----- 搜索 -----
function doTreeSearch() {
    const keyword = document.getElementById("tree_search_input").value.trim();
    const wrapper = document.getElementById("tree_wrapper");

    if (!keyword) {
        renderTree(treeRawData);
        return;
    }

    const filtered = JSON.parse(JSON.stringify(treeRawData));
    filtered.forEach(node => markMatches(node, keyword));
    filtered.forEach(node => pruneUnmatched(node));

    if (filtered.length > 0) {
        renderTree(filtered);
    } else {
        wrapper.innerHTML = '<div class="tree-no-match">没有找到匹配的目录或文件</div>';
    }
}

function clearTreeSearch() {
    document.getElementById("tree_search_input").value = "";
    renderTree(treeRawData);
}

// ----- 初始化 -----
function init() {
    const treePathInput = document.getElementById("tree_path_input");
    const treeLoadBtn = document.getElementById("tree_load_btn");
    const treeIncludeFiles = document.getElementById("tree_include_files");
    const treeErrorMsg = document.getElementById("tree_error_msg");
    const treeStatsBar = document.getElementById("tree_stats_bar");
    const treeStatsText = document.getElementById("tree_stats_text");
    const treeSearchInput = document.getElementById("tree_search_input");
    const treeSearchBtn = document.getElementById("tree_search_btn");
    const treeSearchClearBtn = document.getElementById("tree_search_clear_btn");

    // 恢复上次路径
    const savedPath = sessionStorage.getItem("last_path");
    const savedInclude = sessionStorage.getItem("last_include_files");
    if (savedPath) {
        treePathInput.value = savedPath;
        treeIncludeFiles.checked = savedInclude === "true";
    }

    treeLoadBtn.addEventListener("click", loadTree);
    treePathInput.addEventListener("keypress", (e) => { if (e.key === "Enter") loadTree(); });

    treeSearchBtn.addEventListener("click", doTreeSearch);
    treeSearchClearBtn.addEventListener("click", clearTreeSearch);
    treeSearchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") doTreeSearch();
    });

    async function loadTree() {
        const path = treePathInput.value.trim();
        if (!path) { showError(treeErrorMsg, "请输入目录路径"); return; }
        treeLoadBtn.disabled = true;
        treeLoadBtn.textContent = "加载中...";
        hideError(treeErrorMsg);
        treeStatsBar.style.display = "none";

        try {
            const data = await fetchTree(path, treeIncludeFiles.checked);
            if (data.length === 0) { showError(treeErrorMsg, "目录为空或路径不存在"); return; }

            sessionStorage.setItem("last_path", path);
            sessionStorage.setItem("last_include_files", String(treeIncludeFiles.checked));

            // 深拷贝保存原始数据
            treeRawData = JSON.parse(JSON.stringify(data));

            renderTree(data);

            const td = countDirs(data);
            const tf = countFiles(data);
            treeStatsText.textContent = `共 ${td} 个目录${treeIncludeFiles.checked ? `，${tf} 个文件` : ""}`;
            treeStatsBar.style.display = "block";

            // 显示搜索栏
            document.getElementById("tree_search_bar").style.display = "flex";
        } catch (err) {
            showError(treeErrorMsg, err.message);
        } finally {
            treeLoadBtn.disabled = false;
            treeLoadBtn.textContent = "加载";
        }
    }

    function showError(el, msg) {
        el.textContent = msg;
        el.style.display = "block";
    }

    function hideError(el) {
        el.style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", init);
