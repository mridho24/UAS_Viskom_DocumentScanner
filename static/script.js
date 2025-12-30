// script.js - Smart Document Scanner Client-side Logic

let downloadLinks = {};

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadDropzone = document.querySelector('.upload-dropzone');
    
    if (!fileInput || !uploadDropzone) {
        console.error('Required elements not found');
        return;
    }
    
    // File input change handler
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop handlers
    uploadDropzone.addEventListener('dragover', handleDragOver);
    uploadDropzone.addEventListener('dragleave', handleDragLeave);
    uploadDropzone.addEventListener('drop', handleDrop);
    
    // Click to upload
    uploadDropzone.addEventListener('click', () => fileInput.click());
});

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        uploadFile(file);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file) {
        uploadFile(file);
    }
}

async function uploadFile(file) {
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
        alert('❌ Format file tidak didukung!\nGunakan: JPG, PNG, BMP, TIFF, atau WEBP');
        return;
    }
    
    // Validate file size (16MB)
    if (file.size > 16 * 1024 * 1024) {
        alert('❌ File terlalu besar!\nMaksimal 16MB');
        return;
    }
    
    // Show loading, hide upload section and results
    document.querySelector('.upload-section').classList.add('is-hidden');
    document.getElementById('loadingSection').classList.remove('is-hidden');
    document.getElementById('resultsSection').classList.add('is-hidden');
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Upload and process
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Display results
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Terjadi kesalahan: ' + error.message);
        resetUpload();
    }
}

function displayResults(data) {
    // Hide loading, show results
    document.getElementById('loadingSection').classList.add('is-hidden');
    document.getElementById('resultsSection').classList.remove('is-hidden');
    
    // Set strategy info
    document.getElementById('strategyInfo').textContent = data.strategy;
    
    // Set images
    document.getElementById('imgOriginal').src = 'data:image/jpeg;base64,' + data.images.original;
    document.getElementById('imgCorners').src = 'data:image/jpeg;base64,' + data.images.corners;
    document.getElementById('imgWarped').src = 'data:image/jpeg;base64,' + data.images.warped;
    document.getElementById('imgScanned').src = 'data:image/jpeg;base64,' + data.images.scanned;
    document.getElementById('imgEnhanced').src = 'data:image/jpeg;base64,' + data.images.enhanced;
    
    // Store download links
    downloadLinks = data.download_links;
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

function downloadImage(type) {
    const link = downloadLinks[type];
    if (link) {
        window.open(link, '_blank');
    }
}

function resetUpload() {
    // Reset file input
    document.getElementById('fileInput').value = '';
    
    // Show upload section, hide others
    document.querySelector('.upload-section').classList.remove('is-hidden');
    document.getElementById('loadingSection').classList.add('is-hidden');
    document.getElementById('resultsSection').classList.add('is-hidden');
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
