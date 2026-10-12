import io, unittest
from PIL import Image,ImageDraw,ImageFont
from services.product_scan import available,scan_photo

class LocalOCRTests(unittest.TestCase):
 @unittest.skipUnless(available(),'Tesseract local ausente')
 def test_real_local_ocr_reads_synthetic_product_and_price(self):
  image=Image.new('RGB',(1200,180),'white');draw=ImageDraw.Draw(image)
  try:font=ImageFont.truetype('DejaVuSans.ttf',62)
  except OSError:self.skipTest('Fonte de fixture OCR ausente')
  draw.text((25,40),'Arroz 12,90',font=font,fill='black')
  data=io.BytesIO();image.save(data,format='PNG')
  results=scan_photo(data.getvalue())
  self.assertTrue(any('Arroz' in r['name'] and r['unit_price']=='12.90' for r in results),results)
