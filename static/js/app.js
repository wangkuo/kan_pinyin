(function () {
  "use strict";

  const DEFAULT_GRID = { A4: 16, A5: 14 };
  const DEFAULT_PINYIN = { A4: 10, A5: 9 };

  const el = {
    words: document.getElementById("words"),
    paperGroup: document.getElementById("paper-group"),
    gridSize: document.getElementById("grid-size"),
    gridSizeVal: document.getElementById("grid-size-val"),
    pinyinSize: document.getElementById("pinyin-size"),
    pinyinSizeVal: document.getElementById("pinyin-size-val"),
    showHeader: document.getElementById("show-header"),
    showAnswer: document.getElementById("show-answer"),
    shuffle: document.getElementById("shuffle"),
    showPageNumber: document.getElementById("show-page-number"),
    generate: document.getElementById("generate"),
    download: document.getElementById("download"),
    frame: document.getElementById("pdf-frame"),
    previewHint: document.getElementById("preview-hint"),
    tipsSummary: document.getElementById("tips-summary"),
    tipsList: document.getElementById("tips-list"),
  };

  let paper = "A4";
  let pdfUrl = null;
  let parseTimer = null;
  let lastParsedText = null;

  /* ---------------- 工具 ---------------- */
  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function timestamp() {
    const d = new Date();
    return (
      d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) +
      "_" + pad(d.getHours()) + pad(d.getMinutes())
    );
  }

  function setTips(summary, warnings, isError) {
    el.tipsSummary.textContent = summary;
    el.tipsSummary.classList.toggle("error", !!isError);
    el.tipsList.innerHTML = "";
    (warnings || []).forEach(function (text) {
      const li = document.createElement("li");
      li.textContent = text;
      el.tipsList.appendChild(li);
    });
  }

  function syncLabels() {
    el.gridSizeVal.textContent = parseFloat(el.gridSize.value).toFixed(1) + "mm";
    el.pinyinSizeVal.textContent = parseFloat(el.pinyinSize.value).toFixed(1) + "pt";
  }

  /* ---------------- 参数收集 ---------------- */
  function payload() {
    return {
      words: el.words.value,
      paper: paper,
      grid_size: parseFloat(el.gridSize.value),
      pinyin_font_size: parseFloat(el.pinyinSize.value),
      show_header: el.showHeader.checked,
      show_answer: el.showAnswer.checked,
      shuffle: el.shuffle.checked,
      show_page_number: el.showPageNumber.checked,
    };
  }

  /* ---------------- 纸张切换 ---------------- */
  el.paperGroup.addEventListener("click", function (event) {
    const button = event.target.closest(".seg");
    if (!button) return;

    paper = button.dataset.paper;
    Array.prototype.forEach.call(
      el.paperGroup.querySelectorAll(".seg"),
      function (node) { node.classList.toggle("active", node === button); }
    );

    el.gridSize.value = DEFAULT_GRID[paper];
    el.pinyinSize.value = DEFAULT_PINYIN[paper];
    syncLabels();
  });

  el.gridSize.addEventListener("input", syncLabels);
  el.pinyinSize.addEventListener("input", syncLabels);

  /* ---------------- 解析提示（防抖） ---------------- */
  function scheduleParse() {
    if (parseTimer) clearTimeout(parseTimer);
    parseTimer = setTimeout(runParse, 600);
  }

  async function runParse() {
    const text = el.words.value.trim();
    if (!text) {
      lastParsedText = null;
      setTips("等待输入…", []);
      return;
    }
    if (text === lastParsedText) return;
    lastParsedText = text;

    try {
      const resp = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ words: text }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setTips(data.error || "解析失败", [], true);
        return;
      }
      setTips(
        "解析结果：共 " + data.count + " 个词，" + data.char_count + " 个字",
        data.warnings || []
      );
    } catch (err) {
      /* 网络问题不打断输入，保持上次提示 */
    }
  }

  el.words.addEventListener("input", scheduleParse);

  /* ---------------- 生成 ---------------- */
  async function generate() {
    const text = el.words.value.trim();
    if (!text) {
      setTips("请先输入词语", [], true);
      el.words.focus();
      return;
    }

    el.generate.disabled = true;
    el.generate.textContent = "生成中…";

    try {
      const resp = await fetch("/api/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload()),
      });

      if (!resp.ok) {
        let message = "生成失败，请稍后重试";
        try {
          const data = await resp.json();
          if (data && data.error) message = data.error;
        } catch (err) { /* 忽略解析错误 */ }
        setTips(message, [], true);
        return;
      }

      const blob = await resp.blob();
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      pdfUrl = URL.createObjectURL(blob);

      el.frame.src = pdfUrl;
      el.download.href = pdfUrl;
      el.download.download =
        "看拼音写词语_" + paper + "_" + timestamp() + ".pdf";
      el.download.classList.remove("disabled");

      el.previewHint.textContent = "已生成：" + el.download.download;
    } catch (err) {
      setTips("网络错误，请确认服务是否正常运行", [], true);
    } finally {
      el.generate.disabled = false;
      el.generate.textContent = "生成预览";
    }
  }

  el.generate.addEventListener("click", generate);
  el.words.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") generate();
  });

  /* ---------------- 初始化 ---------------- */
  syncLabels();
  setTips("等待输入…", []);
})();