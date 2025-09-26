import Toastify from "toastify-js";

const bgList = {
  success: "#00a651",
  warning: "#ff6b35",
  error: "#dc2626",
  info: "#0056B3",
};
const infoColor = bgList["info"];

// 全局去重機制
const globalDisplayedMessages = new Set();
let globalIsProcessing = false;

// 定期清理機制
setInterval(() => {
  if (globalDisplayedMessages.size > 5) {
    globalDisplayedMessages.clear();
  }
}, 10000); // 10秒檢查一次

const messagesControl = () => {

  return {

    showAllFrom(jsonRef) {
      // 防止重複處理
      if (globalIsProcessing) return;
      globalIsProcessing = true;
      if (!jsonRef) {
        globalIsProcessing = false;
        return;
      }

      try {
        const content = jsonRef.textContent.trim();

        if (!content) {
          globalIsProcessing = false;
          return;
        }

        const messages = JSON.parse(content);

        if (!Array.isArray(messages)) {
          globalIsProcessing = false;
          return;
        }

        // 限制顯示數量並去重
        messages.slice(0, 5).forEach(({ text, tag }) => {
          const messageId = `${text}-${tag}`;
          if (globalDisplayedMessages.has(messageId)) return;
          globalDisplayedMessages.add(messageId);

          const tagsStr = String(tag || "");
          const type = tagsStr.split(" ")[0] || "info";
          const bg = bgList[type] || infoColor;

          // 創建通知元素
          const toast = Toastify({
            text,
            gravity: "top",
            position: "center",
            close: false, // 關閉原始的關閉按鈕
            duration: 3500,
            offset: {
              y: 10,
            },
            style: {
              background: bg,
              borderRadius: "50px",
              padding: "12px 20px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "5px",
              boxShadow: "none",
              width: "fit-content",
            },
            stopOnFocus: true,
            // 自定義通知內容，添加客製關閉按鈕
            node: (() => {
              // 製作容器
              const container = document.createElement("div");
              container.classList.add("flash-messages-container");

              // 加文字
              const textEl = document.createElement("span");
              textEl.textContent = text;
              textEl.classList.add("flash-messages-text");

              // 客製關閉按鈕
              const closeBtn = document.createElement("button");
              closeBtn.innerHTML = `
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" style="width: 20px; height: 20px; opacity: 0.8;">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              `;
              closeBtn.classList.add("flash-messages-close-btn");

              // 點擊關閉通知功能
              closeBtn.addEventListener("click", () => {
                if (toast && typeof toast.hideToast === "function") {
                  toast.hideToast();
                }
              });

              // 放進容器
              container.appendChild(textEl);
              container.appendChild(closeBtn);

              return container;
            })(),
          });

          // 顯示通知
          toast.showToast();
        });

        globalIsProcessing = false;
      } catch (error) {
        globalIsProcessing = false;
        return;
      }
    },
  };
};

window.messagesControl = messagesControl;
