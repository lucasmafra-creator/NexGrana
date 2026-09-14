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

for (const file of ['supabase_schema.sql','SUPABASE_PATCH_V2_RC.sql','SUPABASE_SECURITY_0_17.sql','MIGRATION_0_18.sql','SQL_ATOMIC_0_18.sql','MIGRATION_0_18_1.sql','MIGRATION_0_19.sql']) {

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
await db.close();
