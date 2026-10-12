"""Technical asset audit; never substitutes for human visual/device approval."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image

def audit(source):
 root=Path(source)/'src/assets/nex/skins/cutouts'
 manifest=json.loads((root/'manifest.json').read_text())
 expected_hashes={Path(v["asset"]).name:v["sha256"] for skin in manifest["skins"] for v in skin["variants"].values()}
 findings=[];checked=0
 for p in sorted(root.glob('*_v3.png')):
  checked+=1;expected=128 if '_avatar_v3' in p.name else 768
  with Image.open(p) as im:
   issues=[]
   if expected_hashes.get(p.name)!=hashlib.sha256(p.read_bytes()).hexdigest():issues.append("MANIFEST_HASH_MISMATCH")
   if im.mode!='RGBA':issues.append('RGBA_REQUIRED')
   if im.size!=(expected,expected):issues.append('UNEXPECTED_SIZE')
   if im.mode=='RGBA':
    alpha=im.getchannel('A');box=alpha.getbbox()
    if alpha.getextrema()!=(0,255):issues.append('TRANSPARENCY_REQUIRED')
    if not box or min(box[:2])<=0 or box[2]>=im.width or box[3]>=im.height:issues.append('CLIPPED_OR_EMPTY')
   findings.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'issues':issues})
 if checked!=72:findings.append({'file':'catalog','issues':['EXPECTED_72_VARIANTS']})
 return {'status':'PASS' if all(not x['issues'] for x in findings) else 'FAIL',
         'kind':'TECHNICAL_ASSET_AUDIT','variant_count':checked,'findings':findings,
         'aesthetic_approval':'MANUAL_REQUIRED','device_approval':'MANUAL_REQUIRED','auto_modified':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--report',default='nex-assets-report.json');a=p.parse_args()
 result=audit(a.source);Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(result['status']+': auditoria técnica de assets; revisão estética/dispositivo continua separada.')
 return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
