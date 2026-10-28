# Case data on Google Shared Drive

## Layout
- One Shared Drive per client (access = the case team only), one folder per case (see `templates/case-structure.md`).
- Client log exports go to `sources/` as received.

## Why mount instead of the Drive connector
The claude.ai Google Drive connector extracts text from documents and is not meant for multi-MB jsonl/csv exports. Skills parse logs with local scripts, so the Shared Drive must look like a local folder.

## Option A: rclone in WSL (to test)
1. Create your own Google OAuth client (Google is retiring rclone's built-in client ID in 2026).
2. `rclone config` -> new remote, type `drive`, answer **Yes** to "Configure this as a Shared Drive", pick the client drive.
3. `rclone mount ir-<client>: ~/cases/<client> --vfs-cache-mode full &`
4. `export IR_CASES_ROOT=~/cases/<client>`

Refs: https://forum.rclone.org/t/is-it-possible-to-run-rclone-in-windows-10-wsl-and-mount-google-drive-in-windows/29303/2 , https://rcloneview.com/support/blog/mount-google-shared-drives-rcloneview

## Option B: Google Drive for desktop (Windows) + WSL (to test)
1. Install Drive for desktop, stream mode; the Shared Drive appears under `G:\Shared drives\<client>`.
2. In WSL: `sudo mkdir -p /mnt/g && sudo mount -t drvfs G: /mnt/g`.
3. Mark the case folder "Available offline" before parsing large files.

## Rules
- Do not sync client data to personal drives or git.
- Workspace admin may need to approve the OAuth app.
