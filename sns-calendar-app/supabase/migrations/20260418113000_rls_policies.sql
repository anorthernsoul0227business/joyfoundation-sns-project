CREATE OR REPLACE FUNCTION public.get_user_org_ids()
RETURNS SETOF UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT org_id
  FROM public.org_members
  WHERE user_id = (SELECT auth.uid());
$$;

CREATE OR REPLACE FUNCTION public.has_org_role(
  p_org_id UUID,
  p_role VARCHAR DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.org_members
    WHERE user_id = (SELECT auth.uid())
      AND org_id = p_org_id
      AND (p_role IS NULL OR role = p_role)
  );
$$;

CREATE OR REPLACE FUNCTION public.can_edit_org(p_org_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.org_members
    WHERE user_id = (SELECT auth.uid())
      AND org_id = p_org_id
      AND role IN ('owner', 'admin', 'editor')
  );
$$;

ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_select" ON public.organizations
  FOR SELECT TO authenticated
  USING (id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "org_update" ON public.organizations
  FOR UPDATE TO authenticated
  USING (public.has_org_role(id, 'owner') OR public.has_org_role(id, 'admin'))
  WITH CHECK (public.has_org_role(id, 'owner') OR public.has_org_role(id, 'admin'));

CREATE POLICY "org_insert" ON public.organizations
  FOR INSERT TO authenticated
  WITH CHECK ((SELECT auth.uid()) = owner_user_id);

CREATE POLICY "org_delete" ON public.organizations
  FOR DELETE TO authenticated
  USING ((SELECT auth.uid()) = owner_user_id);

ALTER TABLE public.org_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "members_select" ON public.org_members
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "members_insert" ON public.org_members
  FOR INSERT TO authenticated
  WITH CHECK (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'));

CREATE POLICY "members_update" ON public.org_members
  FOR UPDATE TO authenticated
  USING (
    (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'))
    AND NOT (user_id = (SELECT auth.uid()) AND role = 'owner')
  );

CREATE POLICY "members_delete" ON public.org_members
  FOR DELETE TO authenticated
  USING (
    (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'))
    AND NOT (user_id = (SELECT auth.uid()) AND role = 'owner')
  );

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profile_select_self" ON public.users
  FOR SELECT TO authenticated
  USING (
    id = (SELECT auth.uid())
    OR id IN (
      SELECT user_id
      FROM public.org_members
      WHERE org_id IN (SELECT public.get_user_org_ids())
    )
  );

CREATE POLICY "profile_update_self" ON public.users
  FOR UPDATE TO authenticated
  USING (id = (SELECT auth.uid()))
  WITH CHECK (id = (SELECT auth.uid()));
