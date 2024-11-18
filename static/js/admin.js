// static/js/admin.js
document.addEventListener('DOMContentLoaded', function() {
    // Графики для отчетов
    const reportCharts = document.querySelectorAll('.report-chart');
    
    reportCharts.forEach(chart => {
        const ctx = chart.getContext('2d');
        const data = JSON.parse(chart.dataset.chartData);
        
        new Chart(ctx, {
            type: chart.dataset.chartType || 'bar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    });

    // Фильтрация и поиск в таблицах
    const tableFilter = document.getElementById('table-filter');
    if (tableFilter) {
        tableFilter.addEventListener('input', function() {
            const searchText = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('tbody tr');
            
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchText) ? '' : 'none';
            });
        });
    }

    // Сортировка таблиц
    const sortableHeaders = document.querySelectorAll('.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            const column = Array.from(this.parentElement.children).indexOf(this);
            const isNumeric = this.dataset.type === 'number';
            
            // Переключение направления сортировки
            const isAscending = !this.classList.contains('asc');
            sortableHeaders.forEach(h => h.classList.remove('asc', 'desc'));
            this.classList.add(isAscending ? 'asc' : 'desc');
            
            // Сортировка строк
            rows.sort((a, b) => {
                const aValue = a.children[column].textContent;
                const bValue = b.children[column].textContent;
                
                if (isNumeric) {
                    return (parseFloat(aValue) - parseFloat(bValue)) * (isAscending ? 1 : -1);
                }
                return aValue.localeCompare(bValue) * (isAscending ? 1 : -1);
            });
            
            // Обновление таблицы
            const tbody = table.querySelector('tbody');
            rows.forEach(row => tbody.appendChild(row));
        });
    });
});