document.addEventListener('DOMContentLoaded', () => {
    // Quote rotation
    const quotes = [
        `"Style is a way to say who you are without having to speak." - Rachel Zoe`,
        `"Fashion is the armor to survive the reality of everyday life." - Bill Cunningham`,
        `"You can have anything you want in life if you dress for it." - Edith Head`,
        `"Elegance is not standing out, but being remembered." - Giorgio Armani`,
        `"Clothes mean nothing until someone lives in them." - Marc Jacobs`
    ];

    const quoteEl = document.getElementById('random-quote');
    const quoteAuthorEl = quoteEl.nextElementSibling;

    function updateQuote() {
        const random = quotes[Math.floor(Math.random() * quotes.length)];
        const [text, author] = random.split(' - ');
        quoteEl.textContent = text;
        quoteAuthorEl.textContent = `- ${author}`;
    }

    // Initial quote
    updateQuote();
    setInterval(updateQuote, 10000);

    // File Upload handling
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const imagePreview = document.getElementById('image-preview');
    const previewArea = document.getElementById('preview-area');
    const previewActions = document.getElementById('preview-actions');
    const placeholderText = previewArea.querySelector('.placeholder-text');
    const removeBtn = document.getElementById('remove-btn');
    const analyzeBtn = document.getElementById('analyze-btn');

    let currentFile = null;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop area
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    fileInput.addEventListener('change', function () {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('image/')) {
                currentFile = file;
                previewFile(file);
                analyzeBtn.disabled = false;
            } else {
                alert('Please upload an image file.');
            }
        }
    }

    function previewFile(file) {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onloadend = function () {
            imagePreview.src = reader.result;
            imagePreview.style.display = 'block';
            placeholderText.style.display = 'none';
            previewActions.style.display = 'block';
        }
    }

    removeBtn.addEventListener('click', () => {
        currentFile = null;
        fileInput.value = '';
        imagePreview.src = '';
        imagePreview.style.display = 'none';
        placeholderText.style.display = 'block';
        previewActions.style.display = 'none';
        analyzeBtn.disabled = true;

        // Hide results if shown
        document.getElementById('results').style.display = 'none';
    });

    // Analyze API Call
    analyzeBtn.addEventListener('click', async () => {
        if (!currentFile) return;

        const loader = document.getElementById('loader');
        const results = document.getElementById('results');
        const gender = document.querySelector('input[name="gender"]:checked').value;

        // UI State
        analyzeBtn.disabled = true;
        loader.style.display = 'block';
        results.style.display = 'none';

        // Prepare form data
        const formData = new FormData();
        formData.append('image', currentFile);
        formData.append('gender', gender);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                populateResults(data);
                loader.style.display = 'none';
                results.style.display = 'flex';
                // Scroll to results
                results.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                alert('Error analyzing image: ' + (data.error || 'Unknown error'));
                loader.style.display = 'none';
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during analysis.');
            loader.style.display = 'none';
        } finally {
            analyzeBtn.disabled = false;
        }
    });

    function populateResults(data) {
        // Skin Tone
        document.getElementById('skin-color-circle').style.backgroundColor = data.skin_tone.hex;
        document.getElementById('skin-category-name').textContent = `${data.skin_tone.category} Complexion`;

        const recs = data.recommendations;

        // Style Rating
        if (recs.style_rating) {
            document.getElementById('style-score').textContent = recs.style_rating.score || "0/10";
            document.getElementById('style-explanation').textContent = recs.style_rating.explanation || "No explanation provided.";
        }

        // Palette
        const paletteList = document.getElementById('palette-list');
        paletteList.innerHTML = '';
        if (recs.color_palette) {
            recs.color_palette.forEach(color => {
                const li = document.createElement('li');
                li.textContent = color;
                paletteList.appendChild(li);
            });
        }

        // Style Feedback
        document.getElementById('style-feedback').textContent = recs.style_feedback || "Stay stylish!";

        // Outfits
        if (recs.outfit_recommendations) {
            document.getElementById('outfit-casual').textContent = recs.outfit_recommendations.casual || "Casual wear suitable for everyday.";
            document.getElementById('outfit-business').textContent = recs.outfit_recommendations.office_formal || "Formals for professional settings.";
            document.getElementById('outfit-party').textContent = recs.outfit_recommendations.party || "Stylish evening wear.";
        }

        // Product Suggestions
        if (recs.product_suggestions) {
            document.getElementById('sug-shirt').textContent = recs.product_suggestions.shirt || "";
            document.getElementById('sug-pants').textContent = recs.product_suggestions.pants || "";
            document.getElementById('sug-shoes').textContent = recs.product_suggestions.shoes || "";
            document.getElementById('sug-accessories').textContent = recs.product_suggestions.accessories || "";
        }

        // Quote
        if (recs.motivational_fashion_quote) {
            const quoteEl = document.getElementById('random-quote');
            const quoteAuthorEl = quoteEl.nextElementSibling;

            let quoteText = recs.motivational_fashion_quote;
            if (quoteText.includes(' - ')) {
                const parts = quoteText.split(' - ');
                quoteEl.textContent = parts[0];
                quoteAuthorEl.textContent = `- ${parts[1]}`;
            } else {
                quoteEl.textContent = `"${quoteText}"`;
                quoteAuthorEl.textContent = "";
            }
        }
    }
});
