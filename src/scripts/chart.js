// Alpine.js 報表圖表預覽組件
function createReportPreview(subdomain, days) {
    return {
    // 狀態管理
    showModal: false,
    loading: false,
    error: false,
    activeTab: 1,
    currentType: '',
    currentCharts: [],

    // 計算屬性
    get modalTitle() {
        const titles = {
            'sales': '銷售分析圖表預覽',
            'tickets': '票券營運圖表預覽',
            'products': '商品表現圖表預覽'
        };
        return titles[this.currentType] || '';
    },

    // 方法
    async openModal(reportType) {
        this.currentType = reportType;
        this.showModal = true;
        this.loading = true;
        this.error = false;
        this.activeTab = 1;

        // 清理之前的圖表
        this.cleanupCharts();

        try {
            await this.loadChartData(reportType);
        } catch (error) {
            console.error('載入圖表數據失敗:', error);
            this.error = true;
        } finally {
            this.loading = false;
        }
    },

    closeModal() {
        this.showModal = false;
        this.cleanupCharts();
        this.currentType = '';
    },

    switchTab(tabNumber) {
        this.activeTab = tabNumber;
    },

    async loadChartData(reportType) {
        // 使用傳入的參數
        const url = `/merchant/api/chart-data/${reportType}/${subdomain}/?days=${days}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '載入圖表數據失敗');
        }

        // 等待下一個 tick 確保 DOM 已渲染
        await this.$nextTick();
        this.renderCharts(reportType, data.data);
    },

    cleanupCharts() {
        this.currentCharts.forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.currentCharts = [];
    },

    renderCharts(reportType, data) {
        const mainCtx = document.getElementById('mainChart')?.getContext('2d');
        const subCtx = document.getElementById('subChart')?.getContext('2d');

        if (!mainCtx || !subCtx) {
            throw new Error('圖表容器未找到');
        }

        if (reportType === 'sales') {
            this.renderSalesCharts(mainCtx, subCtx, data);
        } else if (reportType === 'tickets') {
            this.renderTicketsCharts(mainCtx, subCtx, data);
        } else if (reportType === 'products') {
            this.renderProductsCharts(mainCtx, subCtx, data);
        }
    },

    renderSalesCharts(mainCtx, subCtx, data) {
        // 銷售分析 - 主圖：營收趨勢線圖
        const mainChart = new Chart(mainCtx, {
            type: 'line',
            data: {
                labels: data.trend_labels || [],
                datasets: [{
                    label: '每日營收 (NT$)',
                    data: data.trend_data || [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: '營收趨勢分析'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'NT$ ' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });

        // 輔助圖：金流方式圓餅圖
        const subChart = new Chart(subCtx, {
            type: 'pie',
            data: {
                labels: data.payment_labels || [],
                datasets: [{
                    data: data.payment_data || [],
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: '金流方式使用比例'
                    },
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.currentCharts = [mainChart, subChart];
    },

    renderTicketsCharts(mainCtx, subCtx, data) {
        // 票券營運 - 主圖：使用率圓餅圖
        const mainChart = new Chart(mainCtx, {
            type: 'pie',
            data: {
                labels: data.usage_labels || [],
                datasets: [{
                    data: data.usage_data || [],
                    backgroundColor: ['#10B981', '#EF4444', '#F59E0B']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: '票券使用率統計'
                    },
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // 輔助圖：時間分布橫條圖
        const subChart = new Chart(subCtx, {
            type: 'bar',
            data: {
                labels: data.time_labels || [],
                datasets: [{
                    label: '使用次數',
                    data: data.time_data || [],
                    backgroundColor: 'rgba(59, 130, 246, 0.8)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: '驗證時間分布'
                    }
                },
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });

        this.currentCharts = [mainChart, subChart];
    },

    renderProductsCharts(mainCtx, subCtx, data) {
        // 商品表現 - 主圖：銷售排行橫條圖
        const mainChart = new Chart(mainCtx, {
            type: 'bar',
            data: {
                labels: data.ranking_labels || [],
                datasets: [{
                    label: '銷售數量',
                    data: data.ranking_data || [],
                    backgroundColor: 'rgba(16, 185, 129, 0.8)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'TOP 10 熱銷商品'
                    }
                },
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });

        // 輔助圖：營收貢獻圓餅圖
        const subChart = new Chart(subCtx, {
            type: 'pie',
            data: {
                labels: data.revenue_labels || [],
                datasets: [{
                    data: data.revenue_data || [],
                    backgroundColor: [
                        '#8B5CF6',
                        '#06B6D4',
                        '#F59E0B',
                        '#EF4444',
                        '#10B981',
                        '#6B7280'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: '商品類別營收貢獻'
                    },
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.currentCharts = [mainChart, subChart];
    }
};
}

// 在 Alpine.js 初始化時註冊組件
document.addEventListener('alpine:init', () => {
    Alpine.data('reportPreview', createReportPreview);
});

// 將函數掛載到全域供使用
window.createReportPreview = createReportPreview;