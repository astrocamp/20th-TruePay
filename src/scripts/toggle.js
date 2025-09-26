// 獲取現有的 CSRF token
function getCurrentCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return value;
    }

    // 備案：從 DOM 獲取
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return csrfInput ? csrfInput.value : null;
}

// 從 API 獲取新的 CSRF token 並更新頁面
async function getFreshCsrfToken() {
    try {
        const response = await fetch('/api/csrf-token/');
        if (response.ok) {
            const data = await response.json();
            const newToken = data.csrf_token;

            // 更新頁面上的 CSRF token
            updatePageCsrfToken(newToken);

            return newToken;
        }
    } catch (error) {
        console.warn('無法獲取新的 CSRF token:', error);
    }
    return null;
}

// 更新頁面上的 CSRF token
function updatePageCsrfToken(newToken) {
    // 更新所有 CSRF input 欄位
    const csrfInputs = document.querySelectorAll('input[name="csrfmiddlewaretoken"]');
    csrfInputs.forEach(input => {
        input.value = newToken;
    });

    // 更新 cookie（如果需要的話）
    // document.cookie = `csrftoken=${newToken}; path=/`;
}

// 智能 CSRF token 獲取
async function getCsrfToken(forceRefresh = false) {
    if (forceRefresh) {
        return await getFreshCsrfToken();
    }
    return getCurrentCsrfToken();
}

function ProductToggle() {
    return {
        loading: false,
        isActive: false,

        init(initialActive) {
            this.isActive = initialActive;
        },

        async toggle(productId, subdomain) {
            if (this.loading) return;

            this.loading = true;

            try {
                // 第一次嘗試：使用頁面現有的 token
                let token = getCurrentCsrfToken();
                let response = await fetch(`/marketplace/shop/${subdomain}/${productId}/toggle/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': token
                    }
                });

                // 如果 403，獲取新 token 並更新頁面，然後重試
                if (response.status === 403) {
                    token = await getFreshCsrfToken();
                    if (token) {
                        response = await fetch(`/marketplace/shop/${subdomain}/${productId}/toggle/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': token
                            }
                        });
                    }
                }

                if (!response.ok) {
                    throw new Error(`操作失敗 (${response.status})`);
                }

                const data = await response.json();

                if (data.success) {
                    // Update button state
                    this.isActive = data.is_active;

                    // Update status label
                    const statusElement = document.getElementById(`status-${productId}`);
                    if (data.is_active) {
                        statusElement.textContent = '\u4e0a\u67b6\u4e2d';
                        statusElement.className = 'bg-green-100 text-green-700 px-2 py-0.5 rounded';
                    } else {
                        statusElement.textContent = '\u672a\u4e0a\u67b6';
                        statusElement.className = 'bg-red-100 text-red-700 px-2 py-0.5 rounded';
                    }
                } else {
                    alert('\u64cd\u4f5c\u5931\u6557\uff1a' + data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('\u64cd\u4f5c\u5931\u6557\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66');
            } finally {
                this.loading = false;
            }
        },

        get buttonText() {
            if (this.loading) return '\u8655\u7406\u4e2d...';
            return this.isActive ? '\u4e0b\u67b6' : '\u4e0a\u67b6';
        },

        get buttonClass() {
            const baseClass = 'px-3 py-1 rounded text-sm font-medium transition-colors disabled:opacity-50';
            const colorClass = this.isActive
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-green-500 hover:bg-green-600 text-white';
            return `${baseClass} ${colorClass}`;
        }
    }
}

document.addEventListener('alpine:init', () => {
    Alpine.data('productToggle', ProductToggle);
})
