document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('.search-input');
    const wordTitle = document.querySelector('.word');
    const definitionContent = document.querySelector('.definition-content');
    const carouselInner = document.querySelector('.carousel-inner');
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const clickableToggle = document.getElementById('clickableToggle');

    let searchTimeout;
    let searchHistory = [];
    let currentHistoryIndex = -1;
    let isClickableMode = false;

    function makeTextClickable(text) {
        return text.split(/\b/).map(word => {
            if (/^[a-zA-Z]+$/.test(word)) {
                return `<span class="clickable-word">${word}</span>`;
            }
            return word;
        }).join('');
    }

    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            const word = e.target.value.trim();
            if (word) {
                fetchWordInfo(word, true); // true indicates it's a new search
            }
        }, 500);
    });

    async function fetchWordInfo(word, isNewSearch = false) {
        try {
            const response = await fetch(`/api/word/${word}`);
            const data = await response.json();

            if (data.error) {
                showError('Word not found');
                return;
            }

            // Handle history
            if (isNewSearch) {
                // If we're in the middle of history and doing a new search
                if (currentHistoryIndex < searchHistory.length - 1) {
                    // Remove forward history only if the new word is different
                    if (word !== searchHistory[currentHistoryIndex + 1]) {
                        searchHistory = searchHistory.slice(0, currentHistoryIndex + 1);
                    }
                }
                // Add to history if it's different from the current word
                if (!searchHistory.length || word !== searchHistory[currentHistoryIndex]) {
                    searchHistory.push(word);
                    currentHistoryIndex = searchHistory.length - 1;
                }
            }

            updateNavigationButtons();
            updateUI(word, data);
        } catch (error) {
            console.error('Error:', error);
            showError('Failed to fetch word information');
        }
    }

    function updateUI(word, data) {
        // Update word title
        wordTitle.textContent = word;

        // Update definition
        if (data.definition) {
            const def = data.definition;
            let html = `
                <div class="phonetic">${def.phonetic || ''}</div>
            `;

            def.meanings.forEach(meaning => {
                html += `
                    <div class="part-of-speech">${meaning.partOfSpeech}</div>
                `;

                meaning.definitions.forEach(definition => {
                    const processedDefinition = isClickableMode ? 
                        makeTextClickable(definition.definition) : 
                        definition.definition;

                    const processedExample = definition.example && isClickableMode ? 
                        makeTextClickable(definition.example) : 
                        definition.example;

                    html += `
                        <div class="definition-item">
                            ${processedDefinition}
                            ${definition.example ? `
                                <div class="example">"${processedExample}"</div>
                            ` : ''}
                        </div>
                    `;
                });
            });

            definitionContent.innerHTML = html;
        }

        // Update images
        if (data.images && data.images.length > 0) {
            carouselInner.innerHTML = data.images.map((img, index) => `
                <div class="carousel-item ${index === 0 ? 'active' : ''}" data-bs-interval="3000">
                    <img src="${img}" alt="${word}" class="d-block w-100">
                </div>
            `).join('');
        }
    }

    function showError(message) {
        definitionContent.innerHTML = `<div class="alert alert-danger">${message}</div>`;
        carouselInner.innerHTML = '';
        wordTitle.textContent = 'Word Explorer';
    }

    function updateNavigationButtons() {
        prevButton.disabled = currentHistoryIndex <= 0;
        nextButton.disabled = currentHistoryIndex >= searchHistory.length - 1;

        // Log navigation state for debugging
        console.log('History:', searchHistory);
        console.log('Current Index:', currentHistoryIndex);
    }

    // Navigation button handlers
    prevButton.addEventListener('click', function() {
        if (currentHistoryIndex > 0) {
            currentHistoryIndex--;
            const word = searchHistory[currentHistoryIndex];
            searchInput.value = word;
            fetchWordInfo(word, false); // false indicates it's not a new search
        }
    });

    nextButton.addEventListener('click', function() {
        if (currentHistoryIndex < searchHistory.length - 1) {
            currentHistoryIndex++;
            const word = searchHistory[currentHistoryIndex];
            searchInput.value = word;
            fetchWordInfo(word, false); // false indicates it's not a new search
        }
    });

    // Clickable mode toggle
    clickableToggle.addEventListener('click', function() {
        isClickableMode = !isClickableMode;
        this.classList.toggle('active');
        if (searchInput.value.trim()) {
            fetchWordInfo(searchInput.value.trim(), false);
        }
    });

    // Handle clicks on clickable words
    document.addEventListener('click', function(e) {
        if (isClickableMode && e.target.classList.contains('clickable-word')) {
            const word = e.target.textContent.replace(/[^a-zA-Z]/g, '');
            if (word) {
                searchInput.value = word;
                fetchWordInfo(word, true); // true because clicking a word is a new search
            }
        }
    });

    // Handle modal image (original code)
    document.querySelectorAll('.carousel-item img').forEach(img => {
        img.addEventListener('click', function() {
            document.querySelector('#imageModal img').src = this.src;
        });
    });
});