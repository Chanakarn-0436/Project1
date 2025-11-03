# Supabase Storage Setup Guide

## Issue: Bucket Creation Permission Denied

The error `new row violates row-level security policy` indicates that the current user doesn't have permission to create storage buckets. This is a common issue with Supabase.

## Solution 1: Manual Bucket Creation (Recommended)

### Step 1: Create Bucket via Supabase Dashboard

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project: `kmjrnfskswctcyftjwxn`
3. Navigate to **Storage** in the left sidebar
4. Click **New Bucket**
5. Fill in the details:
   - **Name**: `uploads`
   - **Public bucket**: ✅ Check this box
   - **File size limit**: `104857600` (100MB)
6. Click **Create bucket**

### Step 2: Set Storage Policies (if needed)

If the bucket is created but you still get permission errors, you may need to set storage policies:

1. In the Storage section, click on the `uploads` bucket
2. Go to **Policies** tab
3. Add the following policies:

```sql
-- Allow anyone to upload files
CREATE POLICY "Allow public uploads" ON storage.objects FOR INSERT
TO public
WITH CHECK (bucket_id = 'uploads');

-- Allow anyone to read files
CREATE POLICY "Allow public reads" ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'uploads');

-- Allow anyone to delete files
CREATE POLICY "Allow public deletes" ON storage.objects FOR DELETE
TO public
USING (bucket_id = 'uploads');
```

## Solution 2: Use Service Role Key (Advanced)

If you have access to the service role key, you can use it for bucket creation:

1. Get your service role key from Supabase Dashboard → Settings → API
2. Update your `secrets.toml`:

```toml
SUPABASE_URL = "https://kmjrnfskswctcyftjwxn.supabase.co"
SUPABASE_ANON_KEY = "your_anon_key"
SUPABASE_SERVICE_KEY = "your_service_role_key"  # Add this
STORAGE_BUCKET = "uploads"
```

3. Update the code to use service key for bucket creation (see `supabase_config_service.py`)

## Solution 3: Test with Existing Bucket

If you already have a bucket with a different name, you can:

1. Update `STORAGE_BUCKET` in `secrets.toml` to use the existing bucket name
2. Or create a new bucket with a different name that you have permission to use

## Testing

After setting up the bucket, run:

```bash
python test_connection.py
```

This should show:
- ✅ Bucket 'uploads' exists!
- ✅ Test file uploaded successfully!
- ✅ All tests passed!

## Troubleshooting

### Common Issues:

1. **403 Unauthorized**: Need to create bucket manually or use service role key
2. **Bucket not found**: Check bucket name spelling and case sensitivity
3. **Upload fails**: Check storage policies and bucket permissions

### Check Current Status:

```bash
# Test connection
python test_connection.py

# Run Streamlit test
streamlit run test_upload.py
```
