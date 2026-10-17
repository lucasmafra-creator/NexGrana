from datetime import date
from uuid import uuid4
from .finance_engine import amount,day,split_amount
import calendar

def expense_batch(hid,payer,kind,category,description,value,due,n,automatic,members,ids=None,group=None):
    value=amount(value);due=day(due);n=int(n)
    if not description.strip() or value<=0 or not 1<=n<=360:
        raise ValueError('Informe descrição, valor positivo e até 360 parcelas.')
    ids=ids or [str(uuid4()) for _ in range(n)]
    if len(ids)!=n:raise ValueError('Quantidade de parcelas alterada; reabra o formulário.')
    group=group or str(uuid4())
    result=[]
    for i in range(n):
        y,m=divmod(due.year*12+due.month-1+i,12);m+=1
        d=date(y,m,min(due.day,calendar.monthrange(y,m)[1]))
        result.append(dict(id=ids[i],household_id=hid,payer_member_id=payer,kind=kind,category=category,
            description=f'{description} (Parcela {i+1}/{n})' if n>1 else description.strip(),amount=float(value),
            expense_date=d.strftime('%d/%m/%Y'),month=d.strftime('%m/%Y'),installments_total=n,
            installment_number=i+1,installment_group=group if n>1 else '',automatic_debit=bool(automatic),
            shares=[dict(member_id=mid,amount=float(v)) for mid,v in split_amount(value,members or [payer])]))
    return result
