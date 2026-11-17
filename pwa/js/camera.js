/**
 * SD Finance PWA - Camera & Image Compression Service
 * Efficient canvas-based compression downscaling 12MP/48MP camera photos for instant mobile uploads.
 */
class CameraService {
  constructor() {
    this.maxDimension = 1280;
    this.quality = 0.75;
  }

  async compressImage(file) {
    if (!file || !file.type.startsWith('image/')) {
      throw new Error('Selected file is not an image');
    }

    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let width = img.width;
          let height = img.height;

          // Downscale while preserving aspect ratio
          if (width > height) {
            if (width > this.maxDimension) {
              height = Math.round((height * this.maxDimension) / width);
              width = this.maxDimension;
            }
          } else {
            if (height > this.maxDimension) {
              width = Math.round((width * this.maxDimension) / height);
              height = this.maxDimension;
            }
          }

          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;

          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);

          // Export compressed JPEG
          const dataUrl = canvas.toDataURL('image/jpeg', this.quality);

          canvas.toBlob(
            (blob) => {
              resolve({
                dataUrl,
                blob,
                sizeBytes: blob.size,
                sizeKb: Math.round(blob.size / 1024),
                width,
                height
              });
            },
            'image/jpeg',
            this.quality
          );
        };

        img.onerror = () => reject(new Error('Failed to load image into canvas'));
        img.src = e.target.result;
      };

      reader.onerror = () => reject(new Error('Failed to read image file'));
      reader.readAsDataURL(file);
    });
  }
}

window.cameraService = new CameraService();
