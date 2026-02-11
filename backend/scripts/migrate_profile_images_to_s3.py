#!/usr/bin/env python3
"""
Migrate profile images from local /uploads to S3.

This script:
1. Finds all profile_image_url values starting with '/uploads/' in tb_member_profile_t
2. For each, converts the image to 256x256 WebP
3. Uploads to S3 and updates DB with CDN URL
4. Idempotent: skips rows already migrated to CDN
"""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.database import get_member_db_connection, release_member_db_connection
from agent.image_utils import convert_to_profile_webp
from agent.storage_s3 import upload_profile_webp


def main():
    """Main migration function."""
    conn = get_member_db_connection()
    cur = conn.cursor()

    try:
        # Statistics
        stats = {
            'total': 0,
            'skipped_already_cdn': 0,
            'file_not_found': 0,
            'conversion_failed': 0,
            's3_failed': 0,
            'db_failed': 0,
            'success': 0,
        }

        # Get all rows with local /uploads/ paths
        cur.execute(
            """
            SELECT member_id, profile_image_url
            FROM tb_member_profile_t
            WHERE profile_image_url LIKE '/uploads/%'
            ORDER BY member_id
            """
        )
        rows = cur.fetchall()

        stats['total'] = len(rows)
        print(f"Found {stats['total']} rows with local /uploads/ paths")
        print("=" * 60)

        if stats['total'] == 0:
            print("No migration needed. All profile images are already on CDN.")
            return

        uploads_dir = os.path.join(BACKEND_DIR, "uploads")

        for member_id, old_url in rows:
            print(f"\n[{member_id}] Processing: {old_url}")

            # Extract filename
            filename = os.path.basename(old_url)
            local_path = os.path.join(uploads_dir, filename)

            # Check if file exists
            if not os.path.exists(local_path):
                print(f"  ⚠️  File not found: {local_path}")
                stats['file_not_found'] += 1
                continue

            try:
                # Read and convert image
                with open(local_path, 'rb') as f:
                    image_data = f.read()

                print(f"  📖 Read {len(image_data)} bytes from local file")

                webp_data = convert_to_profile_webp(image_data)
                print(f"  🖼️  Converted to WebP: {len(webp_data)} bytes")

            except Exception as e:
                print(f"  ❌ Conversion failed: {e}")
                stats['conversion_failed'] += 1
                continue

            try:
                # Upload to S3
                s3_key, cdn_url = upload_profile_webp(webp_data)
                print(f"  ☁️  Uploaded to S3: {cdn_url}")

            except Exception as e:
                print(f"  ❌ S3 upload failed: {e}")
                stats['s3_failed'] += 1
                continue

            try:
                # Update DB
                cur.execute(
                    """
                    UPDATE tb_member_profile_t
                    SET profile_image_url = %s
                    WHERE member_id = %s
                    """,
                    (cdn_url, member_id)
                )
                conn.commit()
                print(f"  ✅ DB updated successfully")
                stats['success'] += 1

            except Exception as e:
                conn.rollback()
                print(f"  ❌ DB update failed: {e}")
                stats['db_failed'] += 1

                # Try to clean up S3 object (best-effort)
                try:
                    from agent.storage_s3 import delete_key
                    delete_key(s3_key)
                    print(f"  🗑️  Cleaned up S3 object after DB failure")
                except:
                    pass

        # Final report
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"Total rows processed:     {stats['total']}")
        print(f"✅ Successfully migrated:  {stats['success']}")
        print(f"⚠️  File not found:         {stats['file_not_found']}")
        print(f"❌ Conversion failed:      {stats['conversion_failed']}")
        print(f"❌ S3 upload failed:       {stats['s3_failed']}")
        print(f"❌ DB update failed:       {stats['db_failed']}")

        # Check if any /uploads/ paths remain
        cur.execute(
            "SELECT COUNT(*) FROM tb_member_profile_t WHERE profile_image_url LIKE '/uploads/%'"
        )
        remaining = cur.fetchone()[0]

        print("\n" + "=" * 60)
        if remaining == 0:
            print("✅ SUCCESS: No /uploads/ paths remaining in database!")
        else:
            print(f"⚠️  WARNING: {remaining} /uploads/ paths still remain")
            print("   (These may be files that could not be migrated)")

    except Exception as e:
        print(f"\n❌ Migration script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


if __name__ == '__main__':
    # Verify environment variables
    required_env = ['AWS_BUCKET_NAME', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'CLOUDFRONT_DOMAIN']
    missing = [k for k in required_env if not os.environ.get(k)]

    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set the following in your .env file:")
        for k in missing:
            print(f"  {k}=...")
        sys.exit(1)

    print("Starting migration from /uploads to S3...")
    print(f"S3 Bucket: {os.environ.get('AWS_BUCKET_NAME')}")
    print(f"CDN Domain: {os.environ.get('CLOUDFRONT_DOMAIN')}")
    print()

    main()
