# Automation Jobs

This folder is reserved for future invoice collection modules.

Planned jobs should write into the configured quarterly folder:

- `scanner` -> `active_folder/scans`
- `email` -> `active_folder/email`
- `wix` -> `active_folder/wix`
- `dropbox` -> `active_folder/dropbox`
- `manual` -> `active_folder/manual`

Keep browser automation, email downloading, and source-specific logic here rather
than in request handlers. The desktop UI should start jobs through API routes and
poll status while the job writes files to disk.
