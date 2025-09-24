function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return value;
    }
    return null;
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
                const response = await fetch(`/marketplace/shop/${subdomain}/${productId}/toggle/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    }
                });

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
});

if (typeof Alpine !== 'undefined') {
    Alpine.data('productToggle', ProductToggle);
}