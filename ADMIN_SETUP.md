# Admin portal setup

The portal is at /admin.html. It is **disabled by default** and does not expose any privileged credentials.

1. Create a **dedicated Supabase project** for Stocks-Publishable. The only currently connected project is named *Saint Leo Campus Event Scheduling System*; do not reuse it without an explicit decision.
2. Run `supabase/admin_schema.sql` in the new project's SQL Editor. Create an Auth email/password user, then insert that user's UUID into `public.admin_members` using the commented SQL statement. Do not use a fake email if password recovery is needed.
3. Create `config/admin-public.json` containing `{"url":"https://YOUR-PROJECT.supabase.co","publishableKey":"YOUR-PUBLISHABLE-KEY"}`. The publishable key is intended for public clients; **never** place a service-role/secret key in this repository.
4. Test login and unauthorized access. Run Supabase security advisors before production.

## Current scope and limitations

The admin portal reads public snapshot counts and supports authenticated, RLS-protected add/hide/unhide/remove operations on `admin_tickers`. It does **not** yet modify `config/tickers.json`, change the public website's visible list, trigger GitHub Actions, or create a background job. The existing SEC collector continues unchanged. To make stock management effective on the public site, implement a trusted backend synchronization step that validates the authenticated admin and updates the GitHub configuration via a server-held token; never put GitHub tokens in browser code.

The snapshot is not a live SEC query. GitHub Actions is linked for collection monitoring; refresh execution requires a separate secure dispatcher.
