import unittest
from datetime import datetime,timedelta,timezone
from services.offers import validate_partner_url
from services.affiliate import active_offers
class SimCatalogTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime.now(timezone.utc);self.hosts={'www.partner.com.br'}
  self.row={'source':'sim_labs','url':'https://www.partner.com.br/rice?sku=123','enabled':True,'expires_at':(self.now+timedelta(hours=1)).isoformat(),'price':12.9,'verified_at':self.now.isoformat(),'availability':'in_stock','affiliate':False}
 def test_exact_host_rejects_credentials_ports_subdomains(self):
  self.assertTrue(validate_partner_url(self.row['url'],self.hosts))
  for url in ['https://sub.www.partner.com.br/x','https://www.partner.com.br.evil.com/x','https://user:pwd@www.partner.com.br/x','http://www.partner.com.br/x','https://www.partner.com.br:444/x','https://www.partner.com.br:bad/x','https://www.partner.com.br/x#fragment']:
   self.assertFalse(validate_partner_url(url,self.hosts))
 def test_custom_host_requires_approved_registry(self):
  self.assertEqual(active_offers([self.row],self.now),[])
  self.assertEqual(len(active_offers([self.row],self.now,allowed_hosts=self.hosts)),1)
 def test_stale_missing_future_verification_and_stock_fail_closed(self):
  for change in [{'verified_at':None},{'verified_at':(self.now-timedelta(hours=25)).isoformat()},{'verified_at':(self.now+timedelta(minutes=6)).isoformat()},{'availability':'out_of_stock'},{'enabled':False}]:
   self.assertEqual(active_offers([{**self.row,**change}],self.now,allowed_hosts=self.hosts),[])
 def test_no_price_is_allowed_without_claiming_verified_price(self):
  row={**self.row,'price':None,'verified_at':None}
  self.assertEqual(len(active_offers([row],self.now,allowed_hosts=self.hosts)),1)
if __name__=='__main__':unittest.main()
