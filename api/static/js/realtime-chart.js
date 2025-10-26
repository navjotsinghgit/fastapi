// Simple Real-time Chart Implementation
function initializeRealTimeChart() {
    console.log('Initializing real-time chart...');
    
    // Wait for Chart.js to be available
    if (typeof Chart === 'undefined') {
        console.log('Chart.js not ready, retrying in 500ms...');
        setTimeout(() => initializeRealTimeChart(), 500);
        return;
    }
    
    const ctx = document.getElementById('realtime-chart');
    if (!ctx) {
        console.error('Real-time chart canvas not found!');
        return;
    }
    
    console.log('Canvas element found:', ctx);
    console.log('Canvas dimensions:', ctx.width, 'x', ctx.height);
    
    // Generate initial data
    const labels = [];
    const data = [];
    const now = new Date();
    
    for (let i = 19; i >= 0; i--) {
        const time = new Date(now.getTime() - (i * 30000)); // 30 seconds ago
        labels.push(time.toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        }));
        data.push(40 + Math.random() * 20); // Random data between 40-60
    }
    
    try {
        if (window.realTimeChart) {
            window.realTimeChart.destroy();
        }
        
        window.realTimeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Current Emissions (tonnes CO₂e)',
                    data: data,
                    borderColor: '#32B4CD',
                    backgroundColor: 'rgba(50, 184, 205, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#32B4CD',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 3
                }, {
                    label: 'Target Level',
                    data: new Array(labels.length).fill(48),
                    borderColor: '#22c55e',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.1,
                    fill: false,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart',
                    onProgress: function(animation) {
                        const chartInstance = animation.chart;
                        const ctx = chartInstance.ctx;
                        const dataset = chartInstance.data.datasets[0];
                        const meta = chartInstance.getDatasetMeta(0);
                        
                        // Add glow effect
                        ctx.save();
                        ctx.shadowColor = 'rgba(50, 180, 205, 0.2)';
                        ctx.shadowBlur = 10;
                        ctx.shadowOffsetX = 0;
                        ctx.shadowOffsetY = 0;
                        ctx.restore();
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#F5F5F5',
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                family: "'FKGroteskNeue', 'Inter', sans-serif",
                                size: 13
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.85)',
                        titleColor: '#F5F5F5',
                        bodyColor: '#F5F5F5',
                        borderColor: '#32B4CD',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12,
                        titleFont: {
                            family: "'FKGroteskNeue', 'Inter', sans-serif",
                            size: 14,
                            weight: 600
                        },
                        bodyFont: {
                            family: "'FKGroteskNeue', 'Inter', sans-serif",
                            size: 13
                        },
                        boxPadding: 6
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#F5F5F5',
                            maxTicksLimit: 8,
                            font: {
                                family: "'FKGroteskNeue', 'Inter', sans-serif",
                                size: 12
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.06)',
                            drawBorder: false,
                            tickLength: 0
                        },
                        border: {
                            dash: [6, 6]
                        },
                        title: {
                            display: true,
                            text: 'Time',
                            color: '#F5F5F5',
                            font: {
                                family: "'FKGroteskNeue', 'Inter', sans-serif",
                                size: 13,
                                weight: 500
                            },
                            padding: {
                                top: 15
                            }
                        }
                    },
                    y: {
                        beginAtZero: false,
                        min: 35,
                        max: 65,
                        ticks: {
                            color: '#F5F5F5',
                            padding: 8,
                            font: {
                                family: "'FKGroteskNeue', 'Inter', sans-serif",
                                size: 12
                            },
                            callback: function(value) {
                                return value.toFixed(1) + ' t';
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.06)',
                            drawBorder: false,
                            tickLength: 0
                        },
                        border: {
                            dash: [6, 6]
                        },
                        title: {
                            display: true,
                            text: 'CO₂ Emissions (tonnes)',
                            color: '#F5F5F5',
                            font: {
                                family: "'FKGroteskNeue', 'Inter', sans-serif",
                                size: 13,
                                weight: 500
                            },
                            padding: {
                                bottom: 15
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
        
        console.log('Real-time chart created successfully!');
        
        // Start real-time updates
        if (window.realTimeInterval) {
            clearInterval(window.realTimeInterval);
        }
        
        window.realTimeInterval = setInterval(updateRealTimeChart, 5000); // Update every 5 seconds
        
        // Update current emission display
        updateCurrentEmissionDisplay(data[data.length - 1]);
        
    } catch (error) {
        console.error('Error creating real-time chart:', error);
    }
}

function updateRealTimeChart() {
    if (!window.realTimeChart) return;
    
    const chart = window.realTimeChart;
    const now = new Date();
    const newTime = now.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
    
    // Generate new emission value with some trend
    const lastValue = chart.data.datasets[0].data[chart.data.datasets[0].data.length - 1] || 50;
    const trend = (Math.random() - 0.5) * 0.4; // Small trend
    const variation = (Math.random() - 0.5) * 3; // Random variation
    const newValue = Math.max(35, Math.min(65, lastValue + trend + variation));
    
    // Add new data point
    chart.data.labels.push(newTime);
    chart.data.datasets[0].data.push(newValue);
    chart.data.datasets[1].data.push(48); // Target level
    
    // Keep only last 20 points
    if (chart.data.labels.length > 20) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
        chart.data.datasets[1].data.shift();
    }
    
    // Update chart with smooth transition
    chart.update({
        duration: 750,
        easing: 'easeInOutQuart',
        lazy: false
    });
    
    // Update current emission display
    updateCurrentEmissionDisplay(newValue);
    
    console.log(`Chart updated at ${newTime}: ${newValue.toFixed(2)} tonnes`);
}

function updateCurrentEmissionDisplay(value) {
    const currentEmissionEl = document.getElementById('current-emission');
    if (currentEmissionEl) {
        currentEmissionEl.textContent = value.toFixed(2);
    }
    
    // Update status indicator
    const statusIndicator = document.querySelector('.status-indicator');
    if (statusIndicator) {
        statusIndicator.classList.remove('status-good', 'status-warning', 'status-danger');
        
        if (value > 52) {
            statusIndicator.classList.add('status-danger');
            statusIndicator.textContent = 'HIGH';
        } else if (value > 48) {
            statusIndicator.classList.add('status-warning');
            statusIndicator.textContent = 'MEDIUM';
        } else {
            statusIndicator.classList.add('status-good');
            statusIndicator.textContent = 'GOOD';
        }
    }
}

// Clean up function
function stopRealTimeChart() {
    if (window.realTimeInterval) {
        clearInterval(window.realTimeInterval);
        window.realTimeInterval = null;
    }
    if (window.realTimeChart) {
        window.realTimeChart.destroy();
        window.realTimeChart = null;
    }
}

// Initialize all charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, Chart.js available:', typeof Chart !== 'undefined');
    
    // Initialize Analytics Charts
    initializeAnalyticsCharts();
    // Initialize Real-time Chart
    ensureRealTimeChart();
});

// Alternative initialization method that waits for everything to be ready
function ensureRealTimeChart() {
    if (document.readyState === 'complete' && typeof Chart !== 'undefined') {
        initializeRealTimeChart();
    } else {
        setTimeout(ensureRealTimeChart, 100);
    }
}

// Initialize Analytics Charts
function initializeAnalyticsCharts() {
    // Add smooth fade-in effect to charts
    document.querySelectorAll('.chart-container').forEach(container => {
        container.style.opacity = '0';
        container.style.transform = 'translateY(20px)';
        container.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
        
        setTimeout(() => {
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        }, 100);
    });
    // Monthly Emission Trends Chart
    const trendChart = document.getElementById('trend-chart');
    if (trendChart) {
        new Chart(trendChart, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: [{
                    label: 'Current Year Emissions',
                    data: [2100, 1950, 2300, 2400, 2200, 2100, 1900, 2000, 2150, 2300, 2400, 2350],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Previous Year Emissions',
                    data: [2300, 2200, 2400, 2600, 2500, 2400, 2300, 2400, 2500, 2600, 2700, 2800],
                    borderColor: '#6b7280',
                    backgroundColor: 'rgba(107, 114, 128, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#f3f4f6',
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(17, 24, 39, 0.8)',
                        titleColor: '#f3f4f6',
                        bodyColor: '#e5e7eb',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#f3f4f6',
                            padding: 10,
                            callback: function(value) {
                                return value + ' t';
                            }
                        },
                        title: {
                            display: true,
                            text: 'CO₂ Emissions (tonnes)',
                            color: '#f3f4f6',
                            padding: 10
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#f3f4f6',
                            padding: 10
                        },
                        title: {
                            display: true,
                            text: 'Month',
                            color: '#f3f4f6',
                            padding: 10
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    // Industry Comparison Chart
    const industryChart = document.getElementById('industry-chart');
    if (industryChart) {
        new Chart(industryChart, {
            type: 'doughnut',
            data: {
                labels: ['Manufacturing', 'Energy', 'Transport', 'Agriculture', 'Others'],
                datasets: [{
                    data: [35, 25, 20, 15, 5],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',   // Blue
                        'rgba(239, 68, 68, 0.8)',    // Red
                        'rgba(16, 185, 129, 0.8)',   // Green
                        'rgba(245, 158, 11, 0.8)',   // Yellow
                        'rgba(107, 114, 128, 0.8)'   // Gray
                    ],
                    borderColor: [
                        'rgba(59, 130, 246, 1)',     // Blue
                        'rgba(239, 68, 68, 1)',      // Red
                        'rgba(16, 185, 129, 1)',     // Green
                        'rgba(245, 158, 11, 1)',     // Yellow
                        'rgba(107, 114, 128, 1)'     // Gray
                    ],
                    borderWidth: 2,
                    hoverBackgroundColor: [
                        'rgba(59, 130, 246, 0.9)',   // Blue
                        'rgba(239, 68, 68, 0.9)',    // Red
                        'rgba(16, 185, 129, 0.9)',   // Green
                        'rgba(245, 158, 11, 0.9)',   // Yellow
                        'rgba(107, 114, 128, 0.9)'   // Gray
                    ],
                    hoverBorderColor: [
                        'rgba(59, 130, 246, 1)',     // Blue
                        'rgba(239, 68, 68, 1)',      // Red
                        'rgba(16, 185, 129, 1)',     // Green
                        'rgba(245, 158, 11, 1)',     // Yellow
                        'rgba(107, 114, 128, 1)'     // Gray
                    ],
                    hoverBorderWidth: 3,
                    spacing: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#f3f4f6',
                            padding: 20,
                            font: {
                                family: "'FKGroteskNeue', 'Inter', sans-serif",
                                size: 13,
                                weight: 500
                            },
                            usePointStyle: true,
                            boxWidth: 8,
                            boxHeight: 8,
                            textAlign: 'left'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#f3f4f6',
                        bodyColor: '#e5e7eb',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: {
                            top: 12,
                            right: 16,
                            bottom: 12,
                            left: 16
                        },
                        cornerRadius: 8,
                        titleFont: {
                            family: "'FKGroteskNeue', 'Inter', sans-serif",
                            size: 14,
                            weight: 600
                        },
                        bodyFont: {
                            family: "'FKGroteskNeue', 'Inter', sans-serif",
                            size: 13,
                            weight: 500
                        },
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw}%`;
                            }
                        },
                        boxPadding: 6
                    }
                },
                cutout: '75%',
                radius: '90%',
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 1000,
                    easing: 'easeInOutQuart'
                },
                elements: {
                    arc: {
                        borderAlign: 'inner',
                        borderJoinStyle: 'round'
                    }
                }
            }
        });
    }
}