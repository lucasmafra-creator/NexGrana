"""Optional on-device OCR; photos never leave the device, results need review."""
import csv
import io
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

def available():
    return bool(shutil.which("tesseract"))

def candidates_from_tsv(text):
    groups={}
    for row in csv.DictReader(io.StringIO(text),delimiter="\t"):
        word=str(row.get("text") or "").strip()
        try:confidence=float(row.get("conf",-1))
        except (ValueError,TypeError):continue
        if not word or confidence<35:continue
        key=tuple(row.get(k) for k in ("page_num","block_num","par_num","line_num"))
        groups.setdefault(key,[]).append((word,min(100,confidence)))
    result=[]
    for words in groups.values():
        line=" ".join(word for word,_ in words)
        match=re.search(r"(?:R\$\s*)?(\d{1,6}[,.]\d{2})\s*$",line)
        if not match:continue
        name=line[:match.start()].strip(" -:•")[:150]
        if not name or not any(c.isalpha() for c in name):continue
        result.append({"name":name,"unit_price":match.group(1).replace(",","."),
                       "confidence":round(sum(c for _,c in words)/len(words)),"source":"local_ocr"})
    return result[:12]

def scan_photo(data):
    binary=shutil.which("tesseract")
    if not binary:
        raise RuntimeError("OCR local não instalado neste dispositivo. A entrada manual continua disponível; nenhuma foto foi enviada a um serviço externo.")
    if not data or len(data)>8*1024*1024:
        raise ValueError("Escolha uma foto de até 8 MB")
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        if image.width*image.height>25_000_000:raise ValueError("Foto grande demais para leitura local")
        image.verify()
    with tempfile.TemporaryDirectory(prefix="nex-product-") as folder:
        path=Path(folder)/"photo.png"
        with Image.open(io.BytesIO(data)) as image:image.convert("RGB").save(path)
        result=subprocess.run([binary,str(path),"stdout","--psm","6","tsv"],capture_output=True,text=True,timeout=20,check=False)
        if result.returncode:raise RuntimeError("Não consegui ler a foto localmente. Tente uma imagem mais nítida ou registre manualmente.")
        return candidates_from_tsv(result.stdout[:1_000_000])
