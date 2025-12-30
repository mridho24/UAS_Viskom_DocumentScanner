# app.py
# Flask Web Application for Smart Document Scanner

from flask import Flask, render_template, request, jsonify, send_from_directory
import cv2
import numpy as np
import os
from werkzeug.utils import secure_filename
import base64
from document_scanner import DocumentScanner

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}

# Create folders if not exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def image_to_base64(image):
    """Convert OpenCV image to base64 string"""
    _, buffer = cv2.imencode('.jpg', image)
    return base64.b64encode(buffer).decode('utf-8')

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, BMP, TIFF, WEBP'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process document
        scanner = DocumentScanner()
        results = scanner.process(filepath)
        
        # Save results
        base_name = os.path.splitext(filename)[0]
        
        warped_path = os.path.join(app.config['RESULTS_FOLDER'], f'{base_name}_warped.jpg')
        scanned_path = os.path.join(app.config['RESULTS_FOLDER'], f'{base_name}_scanned.jpg')
        enhanced_path = os.path.join(app.config['RESULTS_FOLDER'], f'{base_name}_enhanced.jpg')
        corners_path = os.path.join(app.config['RESULTS_FOLDER'], f'{base_name}_corners.jpg')
        
        cv2.imwrite(warped_path, results['warped'])
        cv2.imwrite(scanned_path, results['scanned'])
        cv2.imwrite(enhanced_path, results['enhanced'])
        
        corner_img = scanner.get_corner_visualization()
        cv2.imwrite(corners_path, corner_img)
        
        # Convert to base64 for web display
        response = {
            'success': True,
            'strategy': results['strategy'],
            'images': {
                'original': image_to_base64(results['original']),
                'corners': image_to_base64(corner_img),
                'warped': image_to_base64(results['warped']),
                'scanned': image_to_base64(results['scanned']),
                'enhanced': image_to_base64(results['enhanced'])
            },
            'download_links': {
                'warped': f'/download/{base_name}_warped.jpg',
                'scanned': f'/download/{base_name}_scanned.jpg',
                'enhanced': f'/download/{base_name}_enhanced.jpg'
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed file"""
    return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

if __name__ == '__main__':
    print("="*60)
    print("🚀 Smart Document Scanner - Web Application")
    print("="*60)
    print("📄 Proyek Akhir Visi Komputer")
    print("👤 Created by: Muhammad Ridho (2208107010064)")
    print("="*60)
    print("\n✅ Server starting...")
    print("🌐 Open your browser and go to: http://localhost:5000")
    print("\n⚠️  Press CTRL+C to stop the server\n")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
