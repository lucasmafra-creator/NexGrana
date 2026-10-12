-- 0.24.2: deny editing another member's income even in the same family.
-- Household-wide read remains for the existing family consolidated dashboard.
begin;
drop policy if exists tenant_update on public.income;
drop policy if exists tenant_delete on public.income;
create policy tenant_update on public.income for update to authenticated
 using (public.can_write_household(household_id) and created_by=auth.uid())
 with check (public.can_write_household(household_id) and created_by=auth.uid());
create policy tenant_delete on public.income for delete to authenticated
 using (public.can_write_household(household_id) and created_by=auth.uid());
drop policy if exists tenant_update on public.expenses;
drop policy if exists tenant_delete on public.expenses;
create policy tenant_update on public.expenses for update to authenticated
 using (public.can_write_household(household_id) and created_by=auth.uid())
 with check (public.can_write_household(household_id) and created_by=auth.uid());
create policy tenant_delete on public.expenses for delete to authenticated
 using (public.can_write_household(household_id) and created_by=auth.uid());
drop policy if exists shares_write on public.expense_shares;
create policy shares_write on public.expense_shares for all to authenticated
 using (exists(select 1 from public.expenses e where e.id=expense_id
   and e.created_by=auth.uid() and public.can_write_household(e.household_id)))
 with check (exists(select 1 from public.expenses e
   join public.household_members m on m.household_id=e.household_id
   where e.id=expense_id and m.id=member_id and e.created_by=auth.uid()
   and public.can_write_household(e.household_id)));
notify pgrst,'reload schema';
commit;
