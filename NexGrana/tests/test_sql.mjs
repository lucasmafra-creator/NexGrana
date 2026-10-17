process.on('uncaughtException',e=>{console.error(e.message,e.where||'');process.exit(1);});

import { PGlite } from '@electric-sql/pglite';

import fs from 'node:fs';
import {fileURLToPath} from 'node:url';

const db=new PGlite();

await db.exec(`create role anon; create role authenticated; create schema auth;

create table auth.users(id uuid primary key,raw_user_meta_data jsonb default '{}'::jsonb);

create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;

grant usage on schema auth to authenticated,anon; grant execute on function auth.uid() to authenticated,anon;`);

const root=fileURLToPath(new URL('../',import.meta.url));

for (const file of ['supabase_schema.sql','SUPABASE_PATCH_V2_RC.sql','SUPABASE_SECURITY_0_17.sql','MIGRATION_0_18.sql','SQL_ATOMIC_0_18.sql','MIGRATION_0_18_1.sql','MIGRATION_0_19.sql','MIGRATION_0_20.sql','MIGRATION_0_21.sql','MIGRATION_0_22.sql','MIGRATION_0_23.sql']) {

 try {await db.exec(fs.readFileSync(root+file,'utf8').replace('create extension if not exists pgcrypto;',''));console.log('PASS migration '+file);}

 catch(e){console.error('FAIL migration',file,e.message);process.exit(1);}

}

const A='00000000-0000-0000-0000-000000000001', B='00000000-0000-0000-0000-000000000002';

const HA='10000000-0000-0000-0000-000000000001',HB='10000000-0000-0000-0000-000000000002';

const MA='20000000-0000-0000-0000-000000000001',MB='20000000-0000-0000-0000-000000000002';

await db.exec(`insert into auth.users(id) values('${A}'),('${B}');

insert into public.households(id,name,mode,owner_id,invite_code) values('${HA}','A','family','${A}','A_CODE'),('${HB}','B','family','${B}','B_CODE');

insert into public.household_members(id,household_id,user_id,display_name,role) values('${MA}','${HA}','${A}','A','owner'),('${MB}','${HB}','${B}','B','owner');

insert into public.income(household_id,member_id,amount,month,created_by) values('${HB}','${MB}',123,'09/2026','${B}');`);

async function asUser(uid,sql){await db.exec('set role authenticated');await db.query(`select set_config('request.jwt.claim.sub',$1,false)`,[uid]);try{return await db.query(sql);}finally{await db.exec('reset role');}}

async function rejected(name,uid,sql){let rejected=false;try{await asUser(uid,sql);}catch(e){rejected=true;}if(!rejected)throw new Error('Allowed: '+name);console.log('PASS '+name);}

let r=await asUser(A,'select * from public.income');if(r.rows.length)throw new Error('Cross tenant read');console.log('PASS family A cannot read family B');

await rejected('direct join',A,`insert into public.household_members(household_id,user_id,display_name,role) values('${HB}','${A}','intruder','owner')`);

await rejected('cross household member reference',A,`insert into public.income(household_id,member_id,amount,month,created_by) values('${HA}','${MB}',1,'09/2026','${A}')`);

await rejected('placeholder privilege',A,`insert into public.household_members(household_id,display_name,role) values('${HA}','x','owner')`);

await db.exec('set role anon');let denied=false;try{await db.query('select * from public.income');}catch(e){denied=true;}await db.exec('reset role');if(!denied)throw new Error('Anon read');console.log('PASS anon denied');

r=await asUser(A,`update public.income set amount=99 where household_id='${HB}' returning id`);if(r.rows.length)throw new Error('Cross update');console.log('PASS cross update');

r=await asUser(A,`delete from public.income where household_id='${HB}' returning id`);if(r.rows.length)throw new Error('Cross delete');console.log('PASS cross delete');

const CA='80000000-0000-0000-0000-000000000001';
await asUser(A,`insert into public.nex_conversations(id,household_id,member_id,owner_user_id) values('${CA}','${HA}','${MA}','${A}')`);
r=await asUser(B,'select * from public.nex_conversations');if(r.rows.length)throw new Error('Cross chat read');console.log('PASS cross chat read denied');
await rejected('cross conversation member',A,`insert into public.nex_conversations(household_id,member_id,owner_user_id) values('${HA}','${MB}','${A}')`);

let freeConversation=CA;
for(let slot=1;slot<=5;slot++){
 r=await asUser(A,`select public.pin_nex_conversation('${freeConversation}','Assunto ${slot}',null) as id`);
 freeConversation=r.rows[0].id;
}
r=await asUser(A,`select id from public.nex_conversations where household_id='${HA}' and member_id='${MA}' and owner_user_id='${A}' and kind='pinned' and status='active' order by pinned_slot`);
if(r.rows.length!==5)throw new Error('Pinned conversation limit was not filled');
const firstPinned=r.rows[0].id;
await rejected('sixth pinned conversation without replacement',A,`select public.pin_nex_conversation('${freeConversation}','Assunto 6',null)`);
r=await asUser(A,`select public.pin_nex_conversation('${freeConversation}','Assunto 6','${firstPinned}') as id`);
freeConversation=r.rows[0].id;
r=await asUser(A,`select kind,status,count(*)::int as total from public.nex_conversations where household_id='${HA}' and member_id='${MA}' and owner_user_id='${A}' group by kind,status`);
const conversationCounts=Object.fromEntries(r.rows.map(row=>[`${row.kind}:${row.status}`,Number(row.total)]));
if(conversationCounts['pinned:active']!==5||conversationCounts['pinned:archived']!==1||conversationCounts['free:active']!==1)throw new Error('Atomic pinned replacement failed');
console.log('PASS five pinned conversations plus atomic replacement');



const C='00000000-0000-0000-0000-000000000003';

await db.exec(`insert into auth.users(id) values('${C}');`);

await asUser(C,`select public.join_household_by_code('A_CODE','C')`);

await asUser(C,`update public.household_members set role='owner' where user_id='${C}'`);
r=await asUser(C,`select role from public.household_members where user_id='${C}'`);
if(r.rows[0].role!=='member')throw new Error('Member elevated');console.log('PASS member cannot become owner');
await rejected('invalid invitation',C,`select public.join_household_by_code('WRONG','C')`);

const E='30000000-0000-0000-0000-000000000001';

const payload={id:E,household_id:HA,payer_member_id:MA,kind:'Variável',category:'Outros',description:'Atomic',amount:100,expense_date:'03/09/2026',month:'09/2026',installments_total:1,installment_number:1,installment_group:'',automatic_debit:false,shares:[{member_id:MA,amount:100}]};

await asUser(A,`select public.save_expense_batch('${JSON.stringify([payload])}'::jsonb,false)`);

await asUser(A,`select public.save_expense_batch('${JSON.stringify([payload])}'::jsonb,false)`);

r=await asUser(A,`select * from public.expenses where id='${E}'`);if(r.rows.length!==1)throw new Error('Duplicate expense');console.log('PASS atomic expense retry deduplicated');
for(const field of ['category','expense_date','automatic_debit']) {
 const changed={...payload,[field]:field==='automatic_debit'?true:field==='expense_date'?'04/09/2026':'Casa'};
 await rejected('divergent retry '+field,A,`select public.save_expense_batch('${JSON.stringify([changed])}'::jsonb,false)`);
}
await rejected('negative share',A,`select public.save_expense_batch('${JSON.stringify([{...payload,shares:[{member_id:MA,amount:-1},{member_id:MB,amount:101}]}])}'::jsonb,false)`);
await rejected('duplicate share member',A,`select public.save_expense_batch('${JSON.stringify([{...payload,shares:[{member_id:MA,amount:50},{member_id:MA,amount:50}]}])}'::jsonb,false)`);
await rejected('invalid share sum',A,`select public.save_expense_batch('${JSON.stringify([{...payload,id:'30000000-0000-0000-0000-000000000002',shares:[{member_id:MA,amount:50}]}])}'::jsonb,false)`);

await rejected('cross household share',A,`select public.save_expense_batch('${JSON.stringify([{...payload,id:'30000000-0000-0000-0000-000000000002',shares:[{member_id:MB,amount:100}]}])}'::jsonb,false)`);

r=await asUser(A,`select * from public.expenses where id='30000000-0000-0000-0000-000000000002'`);if(r.rows.length)throw new Error('Partial expense');console.log('PASS rollback expense plus shares');

const G='40000000-0000-0000-0000-000000000001',OP='50000000-0000-0000-0000-000000000001';

await asUser(A,`insert into public.financial_goals(id,household_id,name,target_amount,target_date,created_by) values('${G}','${HA}','Goal',100,'2026-12-31','${A}')`);

await asUser(A,`select public.contribute_goal('${G}',50,'${OP}')`);

await asUser(A,`select public.contribute_goal('${G}',50,'${OP}')`);

r=await asUser(A,`select saved_amount from public.financial_goals where id='${G}'`);if(Number(r.rows[0].saved_amount)!==50)throw new Error('Duplicate contribution');console.log('PASS contribution idempotence');

const T='60000000-0000-0000-0000-000000000001',I='70000000-0000-0000-0000-000000000001';
await asUser(A,`insert into public.market_trips(id,household_id,market_name,created_by) values('${T}','${HA}','Test','${A}')`);
await asUser(A,`insert into public.market_items(id,trip_id,household_id,product_name,quantity,unit_price,created_by) values('${I}','${T}','${HA}','Rice',2,3,'${A}')`);
r=await asUser(A,`select cart_total from public.market_trips where id='${T}'`);
if(Number(r.rows[0].cart_total)!==6)throw new Error('Wrong cart sum');console.log('PASS cart recalculated');
await rejected('stale receipt comparison',A,`select public.confirm_market_receipt('${T}',5,6,0)`);
await rejected('other family receipt',B,`select public.confirm_market_receipt('${T}',6,6,0)`);
await asUser(A,`select public.confirm_market_receipt('${T}',6,7,1)`);
await asUser(A,`update public.market_items set quantity=3 where id='${I}'`);
r=await asUser(A,`select cart_total,receipt_total,cashback_amount from public.market_trips where id='${T}'`);
if(Number(r.rows[0].cart_total)!==9||Number(r.rows[0].receipt_total)!==7||Number(r.rows[0].cashback_amount)!==1)throw new Error('Gross receipt was changed');console.log('PASS closed trip edit preserves receipt');
await asUser(A,`delete from public.market_trips where id='${T}'`);
r=await asUser(A,`select * from public.market_items where id='${I}'`);if(r.rows.length)throw new Error('Orphan item');console.log('PASS trip cascade deletion');

await rejected('non-admin inserts affiliate offer',A,`insert into public.affiliate_offers(title,category,url) values('Ataque','Casa','https://meli.la/teste')`);
await rejected('non-QA user resets workspace',A,`select public.reset_qa_workspace('RESETAR_TESTE')`);
await rejected('wrong QA reset phrase',A,`select public.reset_qa_workspace('ERRADO')`);
console.log('PASS 0.21 admin and QA guards');

await db.exec(`insert into public.app_admins(user_id,role) values('${A}','owner')`);
const OFFER='90000000-0000-0000-0000-000000000001';
await asUser(A,`insert into public.affiliate_offers(id,title,subtitle,category,provider,url,original_url,image_url,image_alt,enabled,expires_at,sort_order,source)
 values('${OFFER}','Achado validado','Oferta administrada','Casa','Mercado Livre','https://meli.la/teste','https://meli.la/teste','https://http2.mlstatic.com/teste.jpg','Produto de teste',true,'2099-01-01T00:00:00Z',10,'owner_panel')`);
await asUser(A,`update public.affiliate_offers set title='Achado atualizado' where id='${OFFER}'`);
await rejected('admin panel rejects unsafe image',A,`update public.affiliate_offers set image_url='https://evil.example/teste.jpg' where id='${OFFER}'`);
r=await asUser(B,`delete from public.affiliate_offers where id='${OFFER}' returning id`);
if(r.rows.length)throw new Error('Non-admin deleted affiliate offer');
r=await asUser(A,`select id from public.affiliate_offers where id='${OFFER}'`);
if(r.rows.length!==1)throw new Error('Offer disappeared after denied delete');
console.log('PASS non-admin cannot delete affiliate offer');
r=await asUser(A,`select count(*)::int as total from public.affiliate_offer_audit where offer_id='${OFFER}'`);
if(Number(r.rows[0].total)!==2)throw new Error('Offer insert/update audit missing');
await asUser(A,`delete from public.affiliate_offers where id='${OFFER}'`);
r=await asUser(A,`select count(*)::int as total from public.affiliate_offer_audit where offer_id='${OFFER}'`);
if(Number(r.rows[0].total)!==3)throw new Error('Offer delete audit missing');
console.log('PASS 0.22 admin CRUD, image guard and audit');

const Q1='00000000-0000-0000-0000-000000000011';
const Q2='00000000-0000-0000-0000-000000000012';
const Q3='00000000-0000-0000-0000-000000000013';
const Q4='00000000-0000-0000-0000-000000000014';
const Q5='00000000-0000-0000-0000-000000000015';
const HQ1='10000000-0000-0000-0000-000000000011';
const HQ2='10000000-0000-0000-0000-000000000012';
const HQ3='10000000-0000-0000-0000-000000000013';
const MQ1='20000000-0000-0000-0000-000000000011';
const MQ2='20000000-0000-0000-0000-000000000013';
const MQ3='20000000-0000-0000-0000-000000000014';
const MQ4='20000000-0000-0000-0000-000000000015';
const MQ5='20000000-0000-0000-0000-000000000016';

await db.exec(`
 insert into auth.users(id) values('${Q1}'),('${Q2}'),('${Q3}'),('${Q4}'),('${Q5}');
 insert into public.households(id,name,mode,owner_id,invite_code) values
  ('${HQ1}','QA individual','family','${Q1}','QA_CODE_1'),
  ('${HQ2}','QA como integrante','family','${Q2}','QA_CODE_2'),
  ('${HQ3}','QA com outra conta real','family','${Q4}','QA_CODE_3');
 insert into public.household_members(id,household_id,user_id,display_name,role,status) values
  ('${MQ1}','${HQ1}','${Q1}','QA 1','owner','active'),
  ('${MQ2}','${HQ2}','${Q2}','Dono preservado','owner','active'),
  ('${MQ3}','${HQ2}','${Q3}','QA integrante','member','active'),
  ('${MQ4}','${HQ3}','${Q4}','QA proprietário','owner','active'),
  ('${MQ5}','${HQ3}','${Q5}','Outra conta real','member','active');
 insert into public.qa_testers(user_id,label) values
  ('${Q1}','QA owner placeholders'),('${Q3}','QA member'),('${Q4}','QA protected owner');
`);

await asUser(Q1,`select public.reset_qa_workspace('RESETAR_TESTE')`);
r=await db.query(`select id from public.households where id='${HQ1}'`);
if(r.rows.length)throw new Error('Single-member QA owner workspace was not reset');
console.log('PASS 0.23 QA owner resets single-member workspace');

await asUser(Q3,`select public.reset_qa_workspace('RESETAR_TESTE')`);
r=await db.query(`select user_id from public.household_members where household_id='${HQ2}' order by user_id`);
if(r.rows.length!==1||r.rows[0].user_id!==Q2)throw new Error('QA member reset changed the owner or preserved the QA membership');
console.log('PASS 0.23 QA member leaves family without deleting owner data');

await asUser(Q4,`select public.reset_qa_workspace('RESETAR_TESTE')`);
r=await db.query(`select h.owner_id,m.user_id,m.role from public.households h join public.household_members m on m.household_id=h.id where h.id='${HQ3}'`);
if(r.rows.length!==1||r.rows[0].owner_id!==Q5||r.rows[0].user_id!==Q5||r.rows[0].role!=='owner')throw new Error('QA owner reset did not preserve the family under the successor');
console.log('PASS 0.23 QA owner transfers family and removes only the QA account');
// Legacy scenarios above exercise the old deployed schema. The current gate
// must also apply 0.24 and its additive security patch in upgrade order.
for(const file of ['MIGRATION_0_24.sql','MIGRATION_0_24_1.sql','MIGRATION_0_24_2.sql','MIGRATION_0_24_3.sql','MIGRATION_0_24_4.sql','MIGRATION_0_24_5.sql']){
 await db.exec(fs.readFileSync(root+file,'utf8'));
 console.log('PASS upgrade '+file);
}
const SL='70000000-0000-0000-0000-000000000101';
const SI='70000000-0000-0000-0000-000000000102';
await asUser(A,`insert into public.shopping_lists(id,household_id,member_id,name,budget,created_by) values('${SL}','${HA}','${MA}','Compras',100,'${A}')`);
await asUser(A,`insert into public.shopping_list_items(id,list_id,household_id,name,quantity,unit_price,created_by) values('${SI}','${SL}','${HA}','Arroz',2,10,'${A}')`);
await rejected('another household cannot start a list trip',B,`select public.start_market_trip_from_list('${SL}','Mercado')`);
const firstTrip=(await asUser(A,`select public.start_market_trip_from_list('${SL}','Mercado') as id`)).rows[0].id;
const repeatTrip=(await asUser(A,`select public.start_market_trip_from_list('${SL}','Mercado') as id`)).rows[0].id;
if(firstTrip!==repeatTrip)throw new Error('List trip retry duplicated session');
r=await asUser(A,`select count(*)::int as n from public.market_items where trip_id='${firstTrip}'`);
if(Number(r.rows[0].n)!==1)throw new Error('List trip retry duplicated item');
console.log('PASS list to trip atomic snapshot and retry');
r=await asUser(A,`select public.confirm_market_receipt('${firstTrip}',0,0,0)`);
r=await asUser(A,`select cart_total from public.market_trips where id='${firstTrip}'`);
if(Number(r.rows[0].cart_total)!==0)throw new Error('Unpicked planned item was included in cart');
console.log('PASS unpicked list item is excluded from receipt');
const HQ4='10000000-0000-0000-0000-000000000014';
const MQ6='20000000-0000-0000-0000-000000000017';
await db.exec(`insert into public.households(id,name,mode,owner_id,invite_code)
 values('${HQ4}','QA explicitly enrolled','individual','${Q1}','QA_NEW');
 insert into public.household_members(id,household_id,user_id,display_name,role,status)
 values('${MQ6}','${HQ4}','${Q1}','QA owner','owner','active');`);
await rejected('QA cannot delete an unenrolled own workspace',Q1,
 `select public.reset_qa_workspace('RESETAR_TESTE','${HQ4}')`);
await rejected('another account cannot enroll QA workspace',B,
 `select public.enroll_owned_qa_workspace('${HQ4}','VINCULAR_TESTE')`);
await rejected('QA enrollment needs exact confirmation',Q1,
 `select public.enroll_owned_qa_workspace('${HQ4}','ERRADO')`);
r=await db.query(`select id from public.households where id='${HQ4}'`);
if(r.rows.length!==1)throw new Error('Unenrolled owner data was lost');
r=await asUser(Q1,`select public.enroll_owned_qa_workspace('${HQ4}','VINCULAR_TESTE') as ok`);
if(r.rows[0].ok!==true)throw new Error('Owned QA enrollment failed');
await rejected('other account cannot reset enrolled workspace',B,
 `select public.reset_qa_workspace('RESETAR_TESTE','${HQ4}')`);
await rejected('invalid confirmation cannot replay reset',Q1,
 `select public.reset_qa_workspace('ERRADO','${HQ4}')`);
r=await asUser(Q1,`select public.reset_qa_workspace('RESETAR_TESTE','${HQ4}') as ok`);
if(r.rows[0].ok!==true)throw new Error('Enrolled QA reset failed');
r=await asUser(Q1,`select public.reset_qa_workspace('RESETAR_TESTE','${HQ4}') as ok`);
if(r.rows[0].ok!==true)throw new Error('QA reset replay is not idempotent');
r=await db.query(`select id from public.households where id='${HQ4}'`);
if(r.rows.length)throw new Error('Enrolled QA workspace was not removed');
console.log('PASS 0.24.1 QA marker and idempotent reset');
const HQ5='10000000-0000-0000-0000-000000000015';
const MQ7='20000000-0000-0000-0000-000000000018';
await db.exec(`insert into public.households(id,name,mode,owner_id,invite_code)
 values('${HQ5}','new personal QA space','individual','${Q3}','QA_NEW2');
 insert into public.household_members(id,household_id,user_id,display_name,role,status)
 values('${MQ7}','${HQ5}','${Q3}','QA owner','owner','active');`);
await rejected('non-owner cannot enroll QA sandbox',Q1,
 `select public.enroll_new_qa_workspace('${HQ5}')`);
r=await asUser(Q3,`select public.enroll_new_qa_workspace('${HQ5}') as ok`);
if(r.rows[0].ok!==true)throw new Error('New QA space could not be enrolled');
r=await asUser(Q3,`select public.reset_qa_workspace('RESETAR_TESTE','${HQ5}') as ok`);
if(r.rows[0].ok!==true)throw new Error('New QA space could not be reset');
console.log('PASS new QA personal space auto enrollment contract');
await asUser(Q3,`select public.join_household_by_code('QA_CODE_2','QA returns')`);
r=await asUser(Q3,`select public.reset_qa_workspace('RESETAR_TESTE','${HQ2}') as ok`);
if(r.rows[0].ok!==true)throw new Error('QA member cannot leave family');
r=await db.query(`select owner_id from public.households where id='${HQ2}'`);
if(r.rows.length!==1||r.rows[0].owner_id!==Q2)throw new Error('QA member reset affected owner data');
console.log('PASS QA member leaves without deleting other family data');
const INCOME_C='30000000-0000-0000-0000-000000000099';
await asUser(C,`insert into public.income(id,household_id,member_id,amount,month,created_by)
 values('${INCOME_C}','${HA}','${MA}',123,'09/2026','${C}')`);
r=await asUser(A,`update public.income set amount=1 where id='${INCOME_C}' returning id`);
if(r.rows.length)throw new Error('Same family member edited another member income');
r=await asUser(A,`delete from public.income where id='${INCOME_C}' returning id`);
if(r.rows.length)throw new Error('Same family member deleted another member income');
r=await asUser(C,`update public.income set amount=124 where id='${INCOME_C}' returning id`);
if(r.rows.length!==1)throw new Error('Income author cannot edit their own row');
console.log('PASS same-family income write isolation');
const EXPENSE_C='30000000-0000-0000-0000-000000000098';
await asUser(C,`insert into public.expenses(id,household_id,payer_member_id,amount,month,kind,category,description,expense_date,created_by)
 values('${EXPENSE_C}','${HA}','${MA}',35,'09/2026','Variável','Outros','Criado por C','03/09/2026','${C}')`);
r=await asUser(A,`update public.expenses set amount=1 where id='${EXPENSE_C}' returning id`);
if(r.rows.length)throw new Error('Same family member edited another member expense');
r=await asUser(A,`delete from public.expenses where id='${EXPENSE_C}' returning id`);
if(r.rows.length)throw new Error('Same family member deleted another member expense');
r=await asUser(C,`update public.expenses set amount=36 where id='${EXPENSE_C}' returning id`);
if(r.rows.length!==1)throw new Error('Expense author cannot edit their own row');
console.log('PASS same-family expense write isolation');
const D='00000000-0000-0000-0000-000000000099';
const HD='10000000-0000-0000-0000-000000000099';
const MD='20000000-0000-0000-0000-000000000099';
await db.exec(`insert into auth.users(id) values('${D}');
insert into public.households(id,name,mode,owner_id,invite_code) values('${HD}','Private','individual','${D}','PRIVATE_DELETION');
insert into public.household_members(id,household_id,user_id,display_name,role) values('${MD}','${HD}','${D}','Owner','owner');
insert into public.income(household_id,member_id,amount,month,created_by) values('${HD}','${MD}',19,'09/2026','${D}');`);
await rejected('another account cannot delete individual workspace',A,`select public.delete_my_individual_account('${HD}','EXCLUIR MINHA CONTA')`);
await rejected('individual account deletion needs exact confirmation',D,`select public.delete_my_individual_account('${HD}','EXCLUIR')`);
r=await db.query(`select id from auth.users where id='${D}'`);
if(r.rows.length!==1)throw new Error('Rejected deletion changed the account');
r=await asUser(D,`select public.delete_my_individual_account('${HD}','EXCLUIR MINHA CONTA') as ok`);
if(r.rows[0].ok!==true)throw new Error('Account deletion failed');
r=await db.query(`select id from auth.users where id='${D}'`);
if(r.rows.length)throw new Error('Deleted account remained in auth.users');
r=await db.query(`select id from public.households where id='${HD}'`);
if(r.rows.length)throw new Error('Deleted space remained');
console.log('PASS individual account deletion removes auth and household atomically');
await db.exec(fs.readFileSync(root+'MIGRATION_0_25.sql','utf8'));
await db.exec(fs.readFileSync(root+'MIGRATION_0_25_1.sql','utf8'));
console.log('PASS monthly and scoped chat migrations');
const CR='80000000-0000-0000-0000-000000000099';
const R1='90000000-0000-0000-0000-000000000001', R2='90000000-0000-0000-0000-000000000002';
await asUser(A,`update public.nex_conversations set status='archived' where owner_user_id='${A}' and pinned_slot=1`);
await asUser(A,`insert into public.nex_conversations(id,household_id,member_id,owner_user_id,kind,pinned_slot) values('${CR}','${HA}','${MA}','${A}','pinned',1)`);
const save=(req,stamp)=>`select public.save_nex_message_safe('${CR}','${MA}','user','TEST DATA','${req}','${stamp}') as result`;
await asUser(A,save(R1,'2026-01-01T12:00:00Z'));
await asUser(A,save(R1,'2026-01-01T12:00:00Z'));
r=await asUser(A,`select count(*)::int as n from public.nex_messages where conversation_id='${CR}'`);
if(r.rows[0].n!==1)throw new Error('Duplicate request');console.log('PASS safe message retry');
const purge=(preview)=>`select public.purge_nex_messages('${CR}','${MA}','2026-01-01T11:00:00Z','2026-01-01T13:00:00Z',${preview}) as n`;
r=await asUser(A,purge(true));if(r.rows[0].n!==1)throw new Error('Preview mismatch');
await rejected('cross-account message purge',B,purge(false));
r=await asUser(A,purge(false));if(r.rows[0].n!==1)throw new Error('Purge mismatch');
r=await asUser(A,purge(false));if(r.rows[0].n!==0)throw new Error('Repeated purge changed count');
r=await asUser(A,save(R1,'2026-01-01T12:00:00Z'));
if(r.rows[0].result.state!=='deleted')throw new Error('Deleted request resurrected');
r=await asUser(A,save(R2,'2026-01-01T12:30:00Z'));
if(r.rows[0].result.state!=='deleted')throw new Error('Delayed message resurrected');
r=await asUser(A,`select content,state from public.nex_messages where conversation_id='${CR}'`);
if(r.rows.length!==1||r.rows[0].content!=='[Mensagem removida]')throw new Error('Deleted content retained');
console.log('PASS purge preview, scope, idempotence, content removal and delayed sync');
await db.exec(fs.readFileSync(root+'MIGRATION_0_25_2.sql','utf8'));
const TB='60000000-0000-0000-0000-000000000099',BO='50000000-0000-0000-0000-000000000099';
await asUser(A,`insert into public.market_trips(id,household_id,market_name,budget,created_by) values('${TB}','${HA}','QA market',50,'${A}')`);
const updateBudget=(budget,old,operation)=>`select public.update_market_trip_safe('${TB}',${budget},'QA market',${old},'${operation}')`;
await rejected('cross family budget edit',B,updateBudget(100,50,BO));
await asUser(A,updateBudget(100,50,BO));
await asUser(A,updateBudget(100,50,BO));
r=await asUser(A,`select count(*)::int as n from public.market_budget_events where trip_id='${TB}'`);
if(r.rows[0].n!==1)throw new Error('Budget history duplicated');
await rejected('divergent budget retry',A,updateBudget(99,50,BO));
await rejected('stale budget conflict',A,updateBudget(90,50,'50000000-0000-0000-0000-000000000098'));
await rejected('negative shopping budget',A,updateBudget(-1,100,'50000000-0000-0000-0000-000000000097'));
r=await asUser(A,`select budget from public.market_trips where id='${TB}'`);
if(Number(r.rows[0].budget)!==100)throw new Error('Rejected budget changed session');
console.log('PASS budget history, scoped retry and stale-device conflict');
await db.exec(fs.readFileSync(root+'MIGRATION_0_25_3.sql','utf8'));
const closure=(id,member,h=HA)=>({id,household_id:h,member_id:member,month_start:'2026-01-01',opening_balance:0,closing_balance:15});
const batch=[closure('a0000000-0000-0000-0000-000000000001',null),closure('a0000000-0000-0000-0000-000000000002',MA)];
const closeSQL=rows=>`select public.save_month_closures_safe('${JSON.stringify(rows)}'::jsonb)`;
await rejected('cross-account month closure',B,closeSQL(batch));
await asUser(A,closeSQL(batch));await asUser(A,closeSQL(batch));
r=await asUser(A,`select count(*)::int as n from public.monthly_closures where month_start='2026-01-01'`);
if(r.rows[0].n!==2)throw new Error('Duplicate month carry');
await rejected('invalid member rolls back closure batch',A,closeSQL([{...batch[0],closing_balance:999},closure('a0000000-0000-0000-0000-000000000003',MB)]));
r=await asUser(A,`select closing_balance from public.monthly_closures where id='${batch[0].id}'`);
if(Number(r.rows[0].closing_balance)!==15)throw new Error('Partial closure escaped rollback');
await rejected('ongoing month closure',A,closeSQL(batch.map(row=>({...row,month_start:new Date().toISOString().slice(0,7)+'-01'}))));
console.log('PASS atomic monthly batch, retry, account scope and rollback');

for(const file of ['MIGRATION_0_25_4.sql','MIGRATION_0_25_5.sql']) await db.exec(fs.readFileSync(root+file,'utf8'));
const TF='b0000000-0000-0000-0000-000000000001',IF='b0000000-0000-0000-0000-000000000002',EF='b0000000-0000-0000-0000-000000000003';
await asUser(A,`insert into public.market_trips(id,household_id,market_name,created_by) values('${TF}','${HA}','QA receipt','${A}')`);
await asUser(A,`insert into public.market_items(id,trip_id,household_id,product_name,quantity,unit_price,category,created_by) values('${IF}','${TF}','${HA}','Rice',2,3,'Food','${A}')`);
const finalize=(receipt=7,member=MA,expected=6)=>`select public.finalize_market_expense_safe('${TF}',${expected},${receipt},1,'${member}','2026-10-06','${EF}')`;
await rejected('other family cannot post purchase expense',B,finalize());
await rejected('invalid receipt/cart leaves no expense',A,finalize(7,MA,5));
await rejected('cross-household member cannot receive purchase',A,finalize(7,MB));
await asUser(A,finalize());await asUser(A,finalize());
r=await asUser(A,`select amount from public.expenses where id='${EF}'`);
if(r.rows.length!==1||Number(r.rows[0].amount)!==7)throw new Error('Purchase expense was duplicated or netted against cashback');
r=await asUser(A,`select amount from public.expense_shares where expense_id='${EF}'`);
if(r.rows.length!==1||Number(r.rows[0].amount)!==7)throw new Error('Purchase shares mismatch');
await rejected('posted purchase rejects changed retry',A,finalize(8));
console.log('PASS receipt and expense atomic; retries create one gross expense and share');
const snapshot={product_name:'Rice',quantity:2,unit_price:3,category:'Food',picked:false,deleted_at:null};
const editOp='b0000000-0000-0000-0000-000000000004',undoOp='b0000000-0000-0000-0000-000000000005';
const mutate=(op,expected,values,undo=null)=>`select public.mutate_market_safe('item','${IF}','${op}','${JSON.stringify(expected)}','${JSON.stringify(values)}',${undo?"'"+undo+"'":'null'})`;
await rejected('another family cannot mutate market item',B,mutate(editOp,snapshot,{quantity:3}));
await asUser(A,mutate(editOp,snapshot,{quantity:3}));await asUser(A,mutate(editOp,snapshot,{quantity:3}));
await rejected('stale edit cannot overwrite later device change',A,mutate('b0000000-0000-0000-0000-000000000006',snapshot,{quantity:5}));
await asUser(A,mutate(undoOp,{...snapshot,quantity:3},snapshot,editOp));
await asUser(A,mutate(undoOp,{...snapshot,quantity:3},snapshot,editOp));
await rejected('second undo of same action rejected',A,mutate('b0000000-0000-0000-0000-000000000007',snapshot,snapshot,editOp));
const delOp='b0000000-0000-0000-0000-000000000008';
await asUser(A,mutate(delOp,snapshot,{deleted_at:'2026-10-06T12:00:00+00:00'}));
r=await asUser(A,`select cart_total from public.market_trips where id='${TF}'`);
if(Number(r.rows[0].cart_total)!==0)throw new Error('Soft deleted item counted in cart');
r=await asUser(A,`select amount from public.expenses where id='${EF}'`);
if(Number(r.rows[0].amount)!==7)throw new Error('Market edit changed past ledger');

await asUser(A,mutate('b0000000-0000-0000-0000-000000000009',{...snapshot,deleted_at:'2026-10-06T12:00:00.000000Z'},snapshot,delOp));
await rejected('quantity precision cannot invalidate undo history',A,mutate('b0000000-0000-0000-0000-000000000010',snapshot,{quantity:1.2345}));
console.log('PASS UTC timestamp equivalence during undo');
console.log('PASS reversible market edit/delete, stale-device guard and ledger separation');
await asUser(A,`delete from public.expenses where id='${EF}'`);
await rejected('deleted ledger expense is not resurrected by purchase retry',A,finalize());


await db.exec(fs.readFileSync(root+'MIGRATION_0_25_6.sql','utf8'));
await db.exec(fs.readFileSync(root+'MIGRATION_0_25_6.sql','utf8'));console.log('PASS commercial migration is idempotent');
const ORIGIN='c0000000-0000-0000-0000-000000000001',SO='c0000000-0000-0000-0000-000000000002';
const currentTime=new Date(), stamp=currentTime.toISOString();
const simOffer={id:SO,product_key:`sim:${ORIGIN}:${SO}`,source:'sim_labs',title:'TEST DATA Rice',provider:'TEST DATA store',url:'https://www.partner.com.br/rice',currency:'BRL',price:12.9,previous_price:19.9,verified_at:stamp,expires_at:new Date(+currentTime+3600000).toISOString(),availability:'in_stock',affiliate:false,enabled:true};
const manifest={schema:'sim-labs.offer-catalog/1',origin:ORIGIN,generated_at:stamp,partner_hosts:['www.partner.com.br'],offers:[simOffer],contains_user_finances:false};
const publish=m=>`select public.apply_sim_offer_catalog('${JSON.stringify(m)}'::jsonb) as result`;
await rejected('non-admin cannot publish commercial catalog',B,publish(manifest));
await rejected('missing schema cannot publish',A,publish({...manifest,schema:null}));
await rejected('manifest claiming finances is rejected',A,publish({...manifest,contains_user_finances:true}));
await rejected('unapproved link host rolls back catalog',A,publish({...manifest,offers:[{...simOffer,url:'https://evil.com/x'}]}));
r=await db.query(`select count(*)::int as n from public.offer_partner_hosts where host='www.partner.com.br'`);if(r.rows[0].n)throw new Error('Failed batch registered hosts');
await asUser(A,publish(manifest));r=await asUser(A,publish(manifest));if(r.rows[0].result.status!=='duplicate')throw new Error('Catalog replay not deduplicated');console.log('PASS catalog admin, atomic rollback, manifest validation and exact replay');
r=await asUser(B,`select id from public.affiliate_offers where id='${SO}'`);if(r.rows.length!==1)throw new Error('Approved commercial offer invisible');console.log('PASS approved catalog visible to authenticated users');
for(const url of ['https://www.partner.com.br.evil.com/x','https://user@www.partner.com.br/x','https://www.partner.com.br:1234/x','http://www.partner.com.br/x','https://sub.www.partner.com.br/x'])await rejected('exact partner host rejects '+url,A,`update public.affiliate_offers set url='${url}' where id='${SO}'`);
await rejected('non-admin cannot approve host',B,`insert into public.offer_partner_hosts(host) values('evil.com')`);
await rejected('unverified price cannot publish',A,`update public.affiliate_offers set verified_at=now()-interval '25 hours' where id='${SO}'`);
await rejected('stock unavailable cannot publish',A,`update public.affiliate_offers set availability='out_of_stock' where id='${SO}'`);
await rejected('NaN price rejected',A,`update public.affiliate_offers set price='NaN' where id='${SO}'`);
await rejected('duplicate offer IDs roll back',A,publish({...manifest,generated_at:new Date(+currentTime+1000).toISOString(),offers:[simOffer,simOffer]}));
const paused={...manifest,generated_at:new Date(+currentTime+2000).toISOString(),offers:[{...simOffer,enabled:false}]};
await asUser(A,publish(paused));await rejected('older approved snapshot cannot revive paused offer',A,publish(manifest));
r=await asUser(B,`select id from public.affiliate_offers where id='${SO}'`);if(r.rows.length)throw new Error('Pause not propagated');console.log('PASS pause propagation and late snapshot protection');
// Clock advance in provider verification affects read policy without another bridge call.
await db.exec(`update public.affiliate_offers set enabled=true,verified_at=now()-interval '25 hours' where id='${SO}'` .replace('update public.affiliate_offers', 'alter table public.affiliate_offers disable trigger guard_affiliate_offer; update public.affiliate_offers')+';alter table public.affiliate_offers enable trigger guard_affiliate_offer;');
r=await asUser(B,`select id from public.affiliate_offers where id='${SO}'`);if(r.rows.length)throw new Error('Stale price visible through RLS');console.log('PASS expired verification hidden by read policy');

await db.close();
