
// JavaScript for the StatisticsTab
// Js is loaded into StatisticsGenerator

document.addEventListener('DOMContentLoaded', function () {
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.title = 'Click to sort';
            header.addEventListener('click', () => sortTable(table, index));
        });
    });

    function sortTable(table, colIndex) {
        const rowsArray = Array.from(table.rows).slice(1);
        const isAscending = table.getAttribute('data-sort-dir') !== 'asc';
        table.setAttribute('data-sort-dir', isAscending ? 'asc' : 'desc');

        rowsArray.sort((a, b) => {
            const aText = a.cells[colIndex]?.innerText.trim() || '';
            const bText = b.cells[colIndex]?.innerText.trim() || '';

            const aNum = parseFloat(aText.replace(/,/g, '').replace(/%/g, ''));
            const bNum = parseFloat(bText.replace(/,/g, '').replace(/%/g, ''));

            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAscending ? aNum - bNum : bNum - aNum;
            }
            return isAscending ? aText.localeCompare(bText) : bText.localeCompare(aText);
        });

        const tbody = table.querySelector('tbody') || table;
        rowsArray.forEach(row => tbody.appendChild(row));
    }

    const searchInput = document.getElementById('columnSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function (e) {
            const term = e.target.value.toLowerCase();
            const colTable = document.getElementById('columnInfoTable');
            if (colTable) {
                const rows = Array.from(colTable.rows).slice(1);
                rows.forEach(row => {
                    const colName = row.cells[0]?.textContent.toLowerCase() || '';
                    row.style.display = colName.includes(term) ? '' : 'none';
                });
            }
        });
    }

    const sectionHeaders = document.querySelectorAll('h2');
    sectionHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.title = 'Click to collapse/expand section';
        header.style.display = 'flex';
        header.style.alignItems = 'center';

        const indicator = document.createElement('span');
        indicator.innerHTML = '&#9660;';
        indicator.style.fontSize = '0.7em';
        indicator.style.marginRight = '8px';
        indicator.style.transition = 'transform 0.2s';
        header.prepend(indicator);

        header.addEventListener('click', () => {
            let nextElement = header.nextElementSibling;
            const isCollapsing = indicator.style.transform === 'rotate(-90deg)';

            indicator.style.transform = isCollapsing ? 'rotate(0deg)' : 'rotate(-90deg)';

            while (nextElement && nextElement.tagName !== 'H2') {
                if (isCollapsing) {
                    nextElement.style.display = nextElement.getAttribute('data-original-display') || '';
                } else {
                    if (nextElement.style.display !== 'none') {
                        nextElement.setAttribute('data-original-display', nextElement.style.display);
                    }
                    nextElement.style.display = 'none';
                }
                nextElement = nextElement.nextElementSibling;
            }
        });
    });

    const corrTable = document.getElementById('correlationTable');
    if (corrTable) {
        const rows = corrTable.querySelectorAll('tr');
        rows.forEach((row) => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, colIndex) => {

                const rowHeader = row.cells[0] ? row.cells[0].innerText.trim() : '';
                const headerRow = corrTable.rows[0];
                const colHeader = (headerRow && headerRow.cells[colIndex]) ? headerRow.cells[colIndex].innerText.trim() : '';
                const cellValue = cell.innerText.trim();

                if (rowHeader && colHeader && cellValue) {
                    cell.title = `${rowHeader} vs ${colHeader}: ${cellValue}`;
                    cell.setAttribute('data-orig-opacity', '1');
                }

                cell.addEventListener('mouseenter', () => {
                    if (row.cells[0]) {
                        row.cells[0].style.backgroundColor = 'rgba(37, 99, 235, 0.15)';
                        row.cells[0].style.color = '#1e3a8a';
                        row.cells[0].style.transition = 'all 0.2s';
                    }
                    if (headerRow && headerRow.cells[colIndex]) {
                        headerRow.cells[colIndex].style.backgroundColor = 'rgba(37, 99, 235, 0.15)';
                        headerRow.cells[colIndex].style.color = '#1e3a8a';
                        headerRow.cells[colIndex].style.transition = 'all 0.2s';
                    }
                });

                cell.addEventListener('mouseleave', () => {
                    if (row.cells[0]) {
                        row.cells[0].style.backgroundColor = '';
                        row.cells[0].style.color = '';
                    }
                    if (headerRow && headerRow.cells[colIndex]) {
                        headerRow.cells[colIndex].style.backgroundColor = '';
                        headerRow.cells[colIndex].style.color = '';
                    }
                });
            });
        });
    }

    const thresholdSlider = document.getElementById('corrThreshold');
    const thresholdLabel = document.getElementById('corrThresholdLabel');
    if (thresholdSlider && corrTable) {
        function applyThreshold(e) {
            const threshold = parseFloat(e.target.value);
            if (thresholdLabel) {
                thresholdLabel.textContent = threshold.toFixed(2);
            }

            const rows = corrTable.querySelectorAll('tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, index) => {
                    if (index === 0) return;

                    const valText = cell.textContent || cell.innerText || '';
                    const val = parseFloat(valText.trim());

                    if (!isNaN(val)) {
                        if (!cell.hasAttribute('data-orig-bg')) {
                            cell.setAttribute('data-orig-bg', cell.style.backgroundColor || '');
                        }

                        if (Math.abs(val) >= threshold || Math.abs(val) > 0.999) {
                            cell.style.opacity = '1';
                            cell.style.backgroundColor = cell.getAttribute('data-orig-bg');
                            cell.style.color = '';
                        } else {
                            cell.style.opacity = '0.2';
                            cell.style.backgroundColor = 'transparent';
                            cell.style.color = '#94a3b8';
                        }
                        cell.style.transition = 'all 0.3s ease';
                    }
                });
            });
        }
        thresholdSlider.addEventListener('input', applyThreshold);
        thresholdSlider.addEventListener('change', applyThreshold);
    }

    const missingToggle = document.getElementById('missingDataToggle');
    if (missingToggle) {
        missingToggle.addEventListener('change', function (e) {
            const showOnlyMissing = e.target.checked;
            const colTable = document.getElementById('columnInfoTable');
            const searchBox = document.getElementById('columnSearch');
            const searchTerm = searchBox ? searchBox.value.toLowerCase() : '';

            if (colTable) {
                const rows = Array.from(colTable.rows).slice(1);
                rows.forEach(row => {
                    const missingCell = row.cells[3];
                    const missingCount = parseInt(missingCell ? missingCell.textContent.replace(/,/g, '') : '0');
                    const colName = row.cells[0]?.textContent.toLowerCase() || '';

                    const matchesSearch = colName.includes(searchTerm);
                    const matchesToggle = !showOnlyMissing || missingCount > 0;

                    row.style.display = (matchesSearch && matchesToggle) ? '' : 'none';
                });
            }
        });

        const searchInput = document.getElementById('columnSearch');
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                missingToggle.dispatchEvent(new Event('change'));
            });
        }
    }
});