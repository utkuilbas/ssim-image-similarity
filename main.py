import os
import sqlite3
import cv2
from skimage.metrics import structural_similarity as ssim
from PIL import Image
from tqdm import tqdm

class SSIMSimilarityAnalyzer:
    def __init__(self, db_path="ssim_similarity.db", image_folder="./images", image_limit=None):
        self.db_path = db_path
        self.image_folder = image_folder
        self.image_limit = image_limit  # görsel sınırı
        self.conn = sqlite3.connect(db_path)
        self.setup_database()
        
    def setup_database(self):
        #veritabanı oluşturma
        cursor = self.conn.cursor()
        
        # dosya bilgileri tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ssim benzerlik skorları tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ssim_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image1_id INTEGER,
                image2_id INTEGER,
                ssim_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (image1_id) REFERENCES images (id),
                FOREIGN KEY (image2_id) REFERENCES images (id),
                UNIQUE(image1_id, image2_id)
            )
        ''')
        
        self.conn.commit()
        
    def load_image_files(self):
        #imajları veritabanına kaydetme
        cursor = self.conn.cursor()
        
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        loaded_count = 0
        
        # dosyaları sıralama
        all_files = sorted([f for f in os.listdir(self.image_folder) 
                           if any(f.lower().endswith(ext) for ext in supported_formats)])
        
        # görsel sınırı
        if self.image_limit:
            all_files = all_files[:self.image_limit]
            print(f"Sınır uygulandı: İlk {self.image_limit} görsel işlenecek")
        
        print(f"Toplam {len(all_files)} dosya bulundu")
        
        for filename in all_files:
            file_path = os.path.join(self.image_folder, filename)
            
            try:
                # görsel boyutları
                img = Image.open(file_path)
                width, height = img.size
                img.close()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO images (filename, file_path, width, height)
                    VALUES (?, ?, ?, ?)
                ''', (filename, file_path, width, height))
                
                if cursor.rowcount > 0:
                    loaded_count += 1
                    
            except Exception as e:
                print(f"Dosya işlenirken hata: {filename} - {e}")
                
        self.conn.commit()
        print(f"{loaded_count} yeni dosya veritabanına eklendi.")
        
    def preprocess_image(self, image_path, target_size=(256, 256)):
        """Görseli SSIM hesaplama için hazırla"""
        try:
            # görsel yükle
            image = cv2.imread(image_path)
            if image is None:
                return None
                
            # gri scale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            resized = cv2.resize(gray, target_size)
            
            return resized
            
        except Exception as e:
            print(f"Görsel işleme hatası {image_path}: {e}")
            return None
            
    def calculate_ssim(self, image1_path, image2_path):
        #ssim skoru hesaplama
        try:
            # görsel önhazırlığı
            img1 = self.preprocess_image(image1_path)
            img2 = self.preprocess_image(image2_path)
            
            if img1 is None or img2 is None:
                return None
                
            # ssim hesapla
            score = ssim(img1, img2, data_range=255)
            
            return score
            
        except Exception as e:
            print(f"SSIM hesaplama hatası: {e}")
            return None
            
    def compute_all_ssim_scores(self):
        #tüm görseller için ssim hesaplama
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT id, filename, file_path FROM images")
        images = cursor.fetchall()
        
        total_pairs = len(images) * (len(images) - 1) // 2
        print(f"{len(images)} görsel için toplam {total_pairs} çift hesaplanacak...")
        
        processed_pairs = 0
        
        with tqdm(total=total_pairs, desc="SSIM hesaplama") as pbar:
            for i in range(len(images)):
                for j in range(i + 1, len(images)):
                    image1_id, filename1, path1 = images[i]
                    image2_id, filename2, path2 = images[j]
                    
                    # ssim skorunu hesapla
                    ssim_score = self.calculate_ssim(path1, path2)
                    
                    if ssim_score is not None:
                        # veritabanına kaydetme
                        cursor.execute('''
                            INSERT OR REPLACE INTO ssim_scores 
                            (image1_id, image2_id, ssim_score) 
                            VALUES (?, ?, ?)
                        ''', (image1_id, image2_id, ssim_score))
                        
                    processed_pairs += 1
                    pbar.update(1)
                    
                    if processed_pairs % 100 == 0:
                        self.conn.commit()
                        
        self.conn.commit()
        print(f"Toplam {processed_pairs} SSIM skoru hesaplandı.")
        
    def get_most_similar_images(self, image_name, top_n=10):
        #belirtilen görsele en benzer sonuçları sıralama
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN i1.filename = ? THEN i2.filename
                    ELSE i1.filename
                END as other_image,
                s.ssim_score
            FROM ssim_scores s
            JOIN images i1 ON s.image1_id = i1.id
            JOIN images i2 ON s.image2_id = i2.id
            WHERE i1.filename = ? OR i2.filename = ?
            ORDER BY s.ssim_score DESC
            LIMIT ?
        ''', (image_name, image_name, image_name, top_n))
        
        results = cursor.fetchall()
        return results
        
        
    def find_high_similarity_pairs(self, threshold=0.9):
        #en yüksek ssim skoruna sahip görsel çiftleri
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT i1.filename, i2.filename, s.ssim_score
            FROM ssim_scores s
            JOIN images i1 ON s.image1_id = i1.id
            JOIN images i2 ON s.image2_id = i2.id
            WHERE s.ssim_score > ?
            ORDER BY s.ssim_score DESC
        ''', (threshold,))
        
        high_similarity = cursor.fetchall()
        
        print(f"SSIM skoru {threshold}'den yüksek olan {len(high_similarity)} çift bulundu:")
        for img1, img2, score in high_similarity[:20]:  # ilk 20 imaj
            print(f"{img1} <-> {img2}: {score:.4f}")
            
        return high_similarity
        
    def export_ssim_results(self, output_file="ssim_results.csv"):
        """SSIM sonuçlarını CSV olarak dışa aktar"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT i1.filename, i2.filename, s.ssim_score
            FROM ssim_scores s
            JOIN images i1 ON s.image1_id = i1.id
            JOIN images i2 ON s.image2_id = i2.id
            ORDER BY s.ssim_score DESC
        ''')
        
        results = cursor.fetchall()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("image1,image2,ssim_score\n")
            for img1, img2, score in results:
                f.write(f"{img1},{img2},{score:.6f}\n")
                
        print(f"SSIM sonuçları {output_file} dosyasına kaydedildi.")
        
    def close(self):
        """Veritabanı bağlantısını kapat"""
        self.conn.close()


if __name__ == "__main__":
    analyzer = SSIMSimilarityAnalyzer(
        db_path="ssim-similarity.db",
        image_folder="./dataset/cats/Data",  # imaj datasının yolu
        image_limit=100  # görsel limiti 
    )
    
    try:
        print("1. Dosyalar veritabanına yükleniyor..")
        analyzer.load_image_files()
        
        print("\n2. SSIM skorları hesaplanıyor..")
        analyzer.compute_all_ssim_scores()
        
        print("\n4. Yüksek benzerlik çiftleri:")
        analyzer.find_high_similarity_pairs(threshold=0.8)
        
        print("\n5. Sonuçlar CSV olarak kaydediliyor..")
        analyzer.export_ssim_results()
        
        print("\n6. Örnek sorgu - İlk görsele en benzer 5 görsel:")
        cursor = analyzer.conn.cursor()
        cursor.execute("SELECT filename FROM images LIMIT 1")
        first_image = cursor.fetchone()
        
        if first_image:
            similar_images = analyzer.get_most_similar_images(first_image[0], top_n=5)
            for other_img, score in similar_images:
                print(f"{first_image[0]} <-> {other_img}: {score:.4f}")
                
    except Exception as e:
        print(f"log: Hata oluştu: {e}")
        
    finally:
        analyzer.close()