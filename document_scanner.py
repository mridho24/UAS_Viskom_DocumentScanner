# document_scanner.py
# Core Document Scanner Module - Refactored from notebook

import cv2
import numpy as np
from skimage import exposure
from skimage.filters import threshold_local
import warnings
warnings.filterwarnings('ignore')

class DocumentScanner:
    """Smart Document Scanner with 5-level fallback strategy"""
    
    def __init__(self):
        self.original = None
        self.image = None
        self.gray = None
        self.corners = None
        self.warped = None
        self.scanned = None
        self.enhanced = None
        self.strategy_used = ""
        
    def load_image(self, image_path_or_array):
        """Load image from path or numpy array"""
        if isinstance(image_path_or_array, str):
            self.original = cv2.imread(image_path_or_array)
        else:
            self.original = image_path_or_array
            
        if self.original is None:
            raise ValueError("Could not load image")
        
        # Resize for faster processing
        height, width = self.original.shape[:2]
        max_width = 800
        
        if width > max_width:
            ratio = max_width / width
            self.image = cv2.resize(self.original, None, fx=ratio, fy=ratio, 
                                   interpolation=cv2.INTER_AREA)
        else:
            self.image = self.original.copy()
        
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        return self.image
    
    def preprocess(self):
        """Apply filtering for noise reduction"""
        bilateral = cv2.bilateralFilter(self.gray, 9, 75, 75)
        return bilateral
    
    def detect_edges(self, filtered):
        """Advanced edge detection"""
        edges_combined = np.zeros_like(filtered)
        
        # Multi-scale edge detection
        blurred1 = cv2.GaussianBlur(filtered, (5, 5), 0)
        edges1 = cv2.Canny(blurred1, 30, 100)
        edges_combined = cv2.bitwise_or(edges_combined, edges1)
        
        blurred2 = cv2.GaussianBlur(filtered, (7, 7), 0)
        edges2 = cv2.Canny(blurred2, 40, 120)
        edges_combined = cv2.bitwise_or(edges_combined, edges2)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges_combined = cv2.morphologyEx(edges_combined, cv2.MORPH_CLOSE, kernel)
        edges_combined = cv2.dilate(edges_combined, kernel, iterations=2)
        
        return edges_combined
    
    def is_valid_document_contour(self, contour):
        """Validate if contour is a document"""
        h, w = self.image.shape[:2]
        x, y, w_box, h_box = cv2.boundingRect(contour)
        
        area_contour = cv2.contourArea(contour)
        area_box = w_box * h_box
        
        # Rectangularity check
        if area_contour < 0.7 * area_box:
            return False
        
        # Margin check
        margin = 0.05
        if (x < w * margin or y < h * margin or 
            x + w_box > w * (1 - margin) or y + h_box > h * (1 - margin)):
            return False
        
        # Area check
        if area_contour < w * h * 0.2 or area_contour > w * h * 0.95:
            return False
        
        return True
    
    def find_document_corners(self, contour, tolerances=[0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08]):
        """Approximate contour to 4-point polygon"""
        peri = cv2.arcLength(contour, True)
        
        for tolerance in tolerances:
            approx = cv2.approxPolyDP(contour, tolerance * peri, True)
            if len(approx) == 4:
                return approx
        
        return None
    
    def order_points(self, pts):
        """Order points: TL, TR, BR, BL"""
        rect = np.zeros((4, 2), dtype="float32")
        
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def extract_corners(self):
        """Extract 4 corner points with 5-level strategy"""
        filtered = self.preprocess()
        edges = self.detect_edges(filtered)
        
        # Find contours
        contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, 
                                       cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Filter valid contours
        valid_contours = []
        for cnt in contours[:20]:
            if self.is_valid_document_contour(cnt):
                valid_contours.append(cnt)
        
        document_contour = None
        
        # Strategy 1: Direct approximation
        for idx, contour in enumerate(valid_contours):
            approx = self.find_document_corners(contour)
            if approx is not None:
                document_contour = approx
                self.strategy_used = f"Aproximasi standar (kontur #{idx+1})"
                break
        
        # Strategy 2: Convex hull
        if document_contour is None and len(valid_contours) > 0:
            for idx, contour in enumerate(valid_contours[:5]):
                hull = cv2.convexHull(contour)
                approx = self.find_document_corners(hull)
                if approx is not None:
                    document_contour = approx
                    self.strategy_used = f"Convex hull (kontur #{idx+1})"
                    break
        
        # Strategy 3: Bounding rectangle
        if document_contour is None and len(valid_contours) > 0:
            largest = valid_contours[0]
            x, y, w, h = cv2.boundingRect(largest)
            margin = 5
            document_contour = np.array([
                [[x + margin, y + margin]],
                [[x + w - margin, y + margin]],
                [[x + w - margin, y + h - margin]],
                [[x + margin, y + h - margin]]
            ], dtype=np.float32)
            self.strategy_used = "Bounding rectangle"
        
        # Strategy 4: Edge density analysis
        if document_contour is None:
            h, w = self.image.shape[:2]
            
            top_edges = edges[:h//2, :]
            top_rows = np.sum(top_edges, axis=1)
            top_y = np.argmax(top_rows > np.percentile(top_rows, 80))
            
            bottom_edges = edges[h//2:, :]
            bottom_rows = np.sum(bottom_edges, axis=1)
            bottom_y = h//2 + len(bottom_rows) - np.argmax(bottom_rows[::-1] > np.percentile(bottom_rows, 80))
            
            left_edges = edges[:, :w//2]
            left_cols = np.sum(left_edges, axis=0)
            left_x = np.argmax(left_cols > np.percentile(left_cols, 80))
            
            right_edges = edges[:, w//2:]
            right_cols = np.sum(right_edges, axis=0)
            right_x = w//2 + len(right_cols) - np.argmax(right_cols[::-1] > np.percentile(right_cols, 80))
            
            if (right_x - left_x > w * 0.3 and bottom_y - top_y > h * 0.3):
                document_contour = np.array([
                    [[left_x, top_y]],
                    [[right_x, top_y]],
                    [[right_x, bottom_y]],
                    [[left_x, bottom_y]]
                ], dtype=np.float32)
                self.strategy_used = "Edge density analysis"
        
        # Strategy 5: Fallback to image boundaries
        if document_contour is None:
            h, w = self.image.shape[:2]
            margin = 20
            document_contour = np.array([
                [[margin, margin]],
                [[w-margin, margin]],
                [[w-margin, h-margin]],
                [[margin, h-margin]]
            ], dtype=np.float32)
            self.strategy_used = "⚠ Fallback: Image boundaries"
        
        self.corners = self.order_points(document_contour.reshape(4, 2))
        return self.corners
    
    def transform_perspective(self):
        """Apply perspective transformation"""
        if self.corners is None:
            self.extract_corners()
        
        rect = self.corners
        (tl, tr, br, bl) = rect
        
        # Calculate dimensions
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        # Destination points
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
        
        # Transform
        M = cv2.getPerspectiveTransform(rect, dst)
        self.warped = cv2.warpPerspective(self.image, M, (maxWidth, maxHeight))
        
        return self.warped
    
    def enhance(self):
        """Enhance scanned document"""
        if self.warped is None:
            self.transform_perspective()
        
        warped_gray = cv2.cvtColor(self.warped, cv2.COLOR_BGR2GRAY)
        
        # Adaptive threshold for scanned effect
        T = threshold_local(warped_gray, 21, offset=10, method="gaussian")
        self.scanned = (warped_gray > T).astype("uint8") * 255
        
        # CLAHE enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(warped_gray)
        
        # Sharpening
        kernel_sharp = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel_sharp)
        
        # Denoising
        self.enhanced = cv2.fastNlMeansDenoising(sharpened, None, 10, 7, 21)
        
        return self.scanned, self.enhanced
    
    def process(self, image_input):
        """Complete processing pipeline"""
        self.load_image(image_input)
        self.extract_corners()
        self.transform_perspective()
        self.enhance()
        
        return {
            'original': self.image,
            'warped': self.warped,
            'scanned': self.scanned,
            'enhanced': self.enhanced,
            'strategy': self.strategy_used
        }
    
    def get_corner_visualization(self):
        """Get image with corners marked"""
        corner_img = self.image.copy()
        
        if self.corners is not None:
            corners_int = self.corners.astype(np.int32)
            cv2.drawContours(corner_img, [corners_int], -1, (0, 255, 0), 3)
            
            labels = ['TL', 'TR', 'BR', 'BL']
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
            
            for point, label, color in zip(self.corners, labels, colors):
                pt = tuple(point.astype(int))
                cv2.circle(corner_img, pt, 15, color, -1)
                cv2.circle(corner_img, pt, 18, (255, 255, 255), 2)
                cv2.putText(corner_img, label, (pt[0]-10, pt[1]+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return corner_img
