# Fix: Assignment PDF 404 After Deploy on Render

## The Problem

Every time you deploy an update to Render, assignment documents (PDFs, attachments) return **404 errors**. The files worked right after upload but disappear after the next deploy.

## Root Cause

**Render uses an ephemeral filesystem.** When your service deploys or restarts:

1. Render spins up a fresh instance with your code
2. Any files written to the local disk (e.g., `static/uploads`) are **wiped**
3. The database still has paths like `assignments/assignment_20250118_123456_0_document.pdf`
4. When a user tries to view or download the file, the path no longer exists → **404**

So uploads work until the next deploy, then vanish.

## Solution: Persistent Disk (Required for Paid Plan)

Render’s **Persistent Disk** keeps files across deploys. Disks are only available on **paid plans** (free plan does not support them).

### Step 1: Upgrade to a Paid Plan

In the Render Dashboard, upgrade your web service to a paid plan (Starter or higher).

### Step 2: Add a Persistent Disk

1. Go to your service **csastudentmanagement** in the Render Dashboard
2. Open the **Disks** tab (or **Advanced** when creating the service)
3. Click **Add Disk**
4. Configure:
   - **Name:** `uploads`
   - **Mount Path:** `/data/uploads`
   - **Size:** 1 GB (or more if needed; you can increase later)

5. Save. Render will redeploy your service with the disk attached.

### Step 3: Set the UPLOAD_FOLDER Environment Variable

1. In your service’s **Environment** tab, add:

   ```env
   UPLOAD_FOLDER=/data/uploads
   ```

2. Redeploy if needed so the app uses the new variable.

### Step 4: Verify

- Upload a new assignment PDF
- Deploy a code change
- Open the assignment file again — it should still load.

---

## Alternative: Use render.yaml (Paid Plan)

If you use `render.yaml` and are on a paid plan, uncomment and adjust the disk section:

```yaml
services:
  - type: web
    name: csastudentmanagement
    # ... other config ...
    disk:
      name: uploads
      mountPath: /data
      sizeGB: 1
```

Then set the environment variable `UPLOAD_FOLDER=/data/uploads` in the Render Dashboard (Environment tab).

---

## If You’re on the Free Plan

The free plan does **not** support persistent disks. Options:

1. **Upgrade to paid** – Simplest; follow the steps above.
2. **Use cloud storage (S3/R2)** – Store files in AWS S3 or Cloudflare R2 and serve via URLs. Requires code changes and setup, but works without a disk.

---

## Mount Path Details

- Use a path like `/data` or `/data/uploads`
- The app creates subdirs: `assignments`, `group_assignments`, `discussion_attachments`
- Only data under the mount path survives redeploys

---

## Checklist

- [ ] Upgraded to a paid Render plan  
- [ ] Added a persistent disk with mount path `/data` or `/data/uploads`  
- [ ] Set `UPLOAD_FOLDER=/data/uploads` in the service environment  
- [ ] Redeployed the service  
- [ ] Uploaded a test PDF and confirmed it still works after another deploy  
