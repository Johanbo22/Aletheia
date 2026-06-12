document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.test-card');
    
    cards.forEach(card => {
        const header = card.querySelector('h3');
        const content = card.querySelector('.test-content');
        
        if (header && content) {
            header.title = 'Click to collapse/expand result';
            
            const indicator = document.createElement('span');
            indicator.innerHTML = '&#9660;';
            indicator.className = 'toggle-icon';
            header.prepend(indicator);
            
            header.addEventListener('click', () => {
                const isCollapsed = content.style.display === 'none';
                
                content.style.display = isCollapsed ? 'block' : 'none';
                indicator.style.transform = isCollapsed ? 'rotate(0deg)' : 'rotate(-90deg)';
            });
        }
    });

    const subCards = document.querySelectorAll('.visual-sub-card');
    
    subCards.forEach(subCard => {
        const header = subCard.querySelector('.sub-card-header');
        const content = subCard.querySelector('.sub-card-content');
        const icon = header ? header.querySelector('.sub-toggle-icon') : null;
        
        if (header && content) {
            header.title = 'Click to view graph';
            
            if (icon) {
                icon.style.display = 'inline-block';
                icon.style.transition = 'transform 0.2s ease';
            }

            header.addEventListener('click', (e) => {
                e.stopPropagation();
                const isCollapsed = content.style.display === 'none';
                
                content.style.display = isCollapsed ? 'block' : 'none';
                header.classList.toggle('expanded', isCollapsed);
                
                if (icon) {
                    icon.style.transform = isCollapsed ? 'rotate(90deg)' : 'rotate(0deg)';
                }
            });
        }
    });

    const searchInput = document.getElementById('testSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function (e) {
            const term = e.target.value.toLowerCase();
            cards.forEach(card => {
                const cardText = card.textContent.toLowerCase();
                card.style.display = cardText.includes(term) ? 'block' : 'none';
            });
        });
    }

    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const textToCopy = btn.getAttribute('data-clipboard');

            const textArea = document.createElement('textarea');
            textArea.value = textToCopy;

            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            textArea.style.top = '0';

            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '&#10003; Copied!';
                    btn.style.color = '#166534';
                    btn.style.backgroundColor = '#dcfce7';
                    btn.style.borderColor = '#bbf7d0';

                    setTimeout(() => {
                        btn.innerHTML = originalText;
                        btn.style.color = '';
                        btn.style.backgroundColor = '';
                        btn.style.borderColor = '';
                    }, 2000);
                }
            } catch (err) {
                console.error('Failed to copy text: ', err);
            }

            document.body.removeChild(textArea);
        });
    });
});