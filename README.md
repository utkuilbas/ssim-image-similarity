# SSIM Görsel Benzerlik Analizi Aracı

Bu Python projesi, bir klasördeki görsellerin yapısal benzerlik indeksine (SSIM) göre benzerlik skorlarını hesaplar, SQLite veritabanında saklar ve analiz sonuçlarını CSV olarak dışa aktarır.

## Veriseti

Veriseti: https://www.kaggle.com/datasets/borhanitrash/cat-dataset

## Özellikler

- Görselleri veritabanına kaydeder
- Görsel çiftleri arasında SSIM benzerlik skorlarını hesaplar
- En benzer görselleri listeler
- Belirli bir eşiğin üzerindeki yüksek benzerlikleri gösterir
- Sonuçları CSV formatında dışa aktarır

## 🛠 Gereksinimler

Bu proje aşağıdaki Python kütüphanelerini kullanır:

```
pip install -r requirements.txt
```

Gerekli kütüphaneler:
- opencv-python
- Pillow
- tqdm
- scikit-image


## ⚙️ Kullanım

1. Görsellerin bulunduğu klasörü belirtin:

```python
analyzer = SSIMSimilarityAnalyzer(
    db_path="ssim-similarity.db",
    image_folder="./dataset/cats/Data",
    image_limit=100
)
```

2. Programı çalıştır:

```
python ssim_analyzer.py
```

3. Çıktılar:
- `ssim-similarity.db`: SQLite veritabanı dosyası (görsel ve SSIM verileri burada tutulur)
- `ssim_results.csv`: SSIM skorlarının dışa aktarılmış CSV versiyonu
- Konsol çıktısında: En benzer görseller listelenir

## 📊 Örnek Sorgular

- Belirli bir görsele en benzer 5 görsel:
```
get_most_similar_images(image_name="image1.jpg", top_n=5)
```

- SSIM skoru 0.90’dan büyük olan görsel çiftleri:
```
find_high_similarity_pairs(threshold=0.9)
```

