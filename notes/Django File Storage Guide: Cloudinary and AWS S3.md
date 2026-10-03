# Django File Storage Guide: Cloudinary and AWS S3

A complete guide to storing user-uploaded files (media) in Django using **Cloudinary** and **Amazon S3**, from local development to production.

## Table of Contents

1. [How Django File Storage Works](#1-how-django-file-storage-works)
2. [Cloudinary vs S3: Which One?](#2-cloudinary-vs-s3-which-one)
3. [Local Development Baseline](#3-local-development-baseline)
4. [Cloudinary Setup](#4-cloudinary-setup)
5. [AWS S3 Setup](#5-aws-s3-setup)
6. [Models, Forms, and Templates](#6-models-forms-and-templates)
7. [Switching Storage by Environment](#7-switching-storage-by-environment)
8. [Direct Browser Uploads (Presigned URLs)](#8-direct-browser-uploads-presigned-urls)
9. [Deleting and Cleaning Up Files](#9-deleting-and-cleaning-up-files)
10. [Testing File Uploads](#10-testing-file-uploads)
11. [Security Best Practices](#11-security-best-practices)
12. [Troubleshooting](#12-troubleshooting)
13. [Production Checklist](#13-production-checklist)

---

## 1. How Django File Storage Works

Django separates two kinds of files:

| Type             | What it is                                 | Setting                     | Handled by                 |
| ---------------- | ------------------------------------------ | --------------------------- | -------------------------- |
| **Static files** | Your CSS, JS, images shipped with the code | `STATIC_URL`, `STATIC_ROOT` | `collectstatic`            |
| **Media files**  | Files users upload (avatars, documents)    | `MEDIA_URL`, `MEDIA_ROOT`   | `FileField` / `ImageField` |

Every `FileField` saves through a **storage backend**. By default that is `FileSystemStorage`, which writes to your server's disk. This is a problem in production because many hosts (Heroku, Render, Railway, containers) have **ephemeral disks**: uploaded files vanish on every redeploy or restart.

The fix is to swap the storage backend for a cloud service. Your models and views stay the same.

Since Django 4.2, backends are configured with the `STORAGES` setting:

```python
STORAGES = {
    "default": {"BACKEND": "..."},       # used for media uploads
    "staticfiles": {"BACKEND": "..."},   # used for collectstatic
}
```

> On Django older than 4.2, use `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE` instead.

---

## 2. Cloudinary vs S3: Which One?

|                            | **Cloudinary**                                        | **AWS S3**                                                                    |
| -------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------- |
| Best for                   | Images and video with on-the-fly transforms           | Any file type, full control, large scale                                      |
| Setup effort               | Low: three credentials                                | Medium: bucket, IAM user, policies                                            |
| Image resize/crop/format   | Built in via URL parameters                           | Not built in (add CloudFront + Lambda, or `django-imagekit`/`sorl-thumbnail`) |
| CDN                        | Included                                              | Add CloudFront separately                                                     |
| Non-image files (PDF, ZIP) | Supported as "raw" files, with caveats                | Native, no caveats                                                            |
| Pricing model              | Credits (storage + bandwidth + transforms), free tier | Pay per GB stored and transferred                                             |
| Lock-in                    | Higher (URLs and transforms are Cloudinary-specific)  | Low (S3 API is widely compatible)                                             |

**Rule of thumb:** use Cloudinary when your app is image-heavy and you want quick wins (thumbnails, WebP/AVIF, cropping). Use S3 for general file storage, documents, backups, or when you need fine-grained control and predictable cost.

You can also use both: Cloudinary for images, S3 for documents (see [section 6.4](#64-using-different-storages-per-field)).

---

## 3. Local Development Baseline

Start with plain local storage so you can develop without cloud accounts.

```python
# settings.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

```python
# urls.py (project)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ...
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

Add `media/` to `.gitignore`. For image fields install Pillow:

```bash
pip install Pillow
```

---

## 4. Cloudinary Setup

### 4.1 Create an account and get credentials

1. Sign up at [cloudinary.com](https://cloudinary.com).
2. Open the **Dashboard**. Copy your **Cloud name**, **API Key**, and **API Secret**.

### 4.2 Install

```bash
pip install cloudinary django-cloudinary-storage
```

### 4.3 Environment variables

```env
# .env (never commit this)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=your-api-secret
```

### 4.4 Settings

```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

INSTALLED_APPS = [
    # 'cloudinary_storage' must come BEFORE 'django.contrib.staticfiles'
    "cloudinary_storage",
    "django.contrib.staticfiles",
    "cloudinary",
    # ... your apps
]

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        # Keep static files on WhiteNoise (or your web server), not Cloudinary
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"  # still required by Django, though URLs come from Cloudinary
```

For static files, install WhiteNoise (`pip install whitenoise`) and add `"whitenoise.middleware.WhiteNoiseMiddleware"` right after `SecurityMiddleware` in `MIDDLEWARE`.

### 4.5 Storage classes by file type

Cloudinary treats files as different **resource types**. Pick the matching storage:

| Storage class                                            | Use for                               |
| -------------------------------------------------------- | ------------------------------------- |
| `cloudinary_storage.storage.MediaCloudinaryStorage`      | Images (default choice)               |
| `cloudinary_storage.storage.VideoMediaCloudinaryStorage` | Video                                 |
| `cloudinary_storage.storage.RawMediaCloudinaryStorage`   | Everything else (ZIP, DOCX, TXT, ...) |

### 4.5.1 Use it in a model (standard FileField)

```python
# models.py
from django.db import models


class Profile(models.Model):
    name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
```

With the default storage set to Cloudinary, `avatar` uploads automatically and `profile.avatar.url` returns a Cloudinary URL.

### 4.6 Alternative: `CloudinaryField`

`CloudinaryField` stores the Cloudinary public ID and gives you transformation helpers.

```python
# models.py
from django.db import models
from cloudinary.models import CloudinaryField


class Product(models.Model):
    title = models.CharField(max_length=200)
    image = CloudinaryField("image", folder="products", blank=True, null=True)
```

If you use `CloudinaryField` without `django-cloudinary-storage`, configure the SDK directly:

```python
# settings.py
import cloudinary

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)
```

Alternatively set a single `CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME` environment variable and the SDK reads it automatically.

### 4.7 Image transformations

One of Cloudinary's main benefits. Transform on the fly through the URL:

```python
# In Python
url = product.image.build_url(width=300, height=300, crop="fill", quality="auto", fetch_format="auto")
```

```html
<!-- In a template -->
{% load cloudinary %} {% cloudinary product.image width=300 height=300
crop="fill" quality="auto" fetch_format="auto" %}
```

`quality="auto"` and `fetch_format="auto"` serve optimized formats (WebP/AVIF) per browser, which often cuts image weight significantly.

### 4.8 Upload presets and folders (optional)

- Use `folder="products"` on the field, or a dynamic `upload_to` path, to keep your Media Library organized.
- Create **upload presets** in the Cloudinary console to enforce rules (allowed formats, max size, auto-tagging, moderation).

---

## 5. AWS S3 Setup

### 5.1 Create the bucket

1. In the AWS Console, open **S3 → Create bucket**.
2. Choose a globally unique name (e.g. `myproject-media-prod`) and a region close to your users.
3. Leave **Block all public access** ON (recommended; see [5.4](#54-public-vs-private-files)).
4. Leave **ACLs disabled** (the default, "Bucket owner enforced"). Modern buckets work this way.

### 5.2 Create an IAM user with least privilege

Don't use your root account or admin keys. Create a dedicated IAM user (or, better, an IAM **role** if you run on EC2/ECS/Lambda; then you need no keys at all).

Attach a policy limited to your bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::myproject-media-prod"
    },
    {
      "Sid": "ObjectAccess",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::myproject-media-prod/*"
    }
  ]
}
```

Create an **access key** for that user and save the Access Key ID and Secret Access Key.

### 5.3 Install and configure Django

```bash
pip install django-storages boto3
# or: pip install "django-storages[s3]"
```

```env
# .env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=myproject-media-prod
AWS_S3_REGION_NAME=eu-central-1
```

```python
# settings.py
import os

INSTALLED_APPS = [
    # ...
    "storages",
]

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "region_name": os.getenv("AWS_S3_REGION_NAME"),
            "file_overwrite": False,      # add random suffix instead of overwriting same-name files
            "default_acl": None,          # required for buckets with ACLs disabled
            "querystring_auth": True,     # signed, expiring URLs (private files)
            "querystring_expire": 3600,   # seconds
            "signature_version": "s3v4",
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

> If running on AWS with an IAM role, omit `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. boto3 picks up the role credentials automatically.

> On Django older than 4.2 or older django-storages, the equivalent settings are `DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"` plus `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_FILE_OVERWRITE = False`, `AWS_DEFAULT_ACL = None`, and so on.

### 5.4 Public vs private files

| Mode                                                  | Settings                                              | Result                                                  |
| ----------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| **Private** (default, recommended for user documents) | `querystring_auth: True`                              | URLs are signed and expire. Bucket stays fully private. |
| **Public** (e.g. avatars, product photos)             | `querystring_auth: False` + public-read bucket policy | Clean permanent URLs, no expiry.                        |

For public media, turn off "Block public access" **only if needed** and add a bucket policy limiting public reads to a prefix:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadMedia",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::myproject-media-prod/public/*"
    }
  ]
}
```

The better production pattern is to keep the bucket private and serve through **CloudFront** (see [5.6](#56-cloudfront-cdn-recommended)).

### 5.5 CORS (needed for browser-side uploads or fonts/images used by JS)

S3 bucket → **Permissions → CORS**:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["https://yourdomain.com", "http://localhost:8000"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

### 5.6 CloudFront CDN (recommended)

Put CloudFront in front of the bucket for faster delivery and cheaper bandwidth, then point Django at it:

```python
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "region_name": os.getenv("AWS_S3_REGION_NAME"),
            "custom_domain": "media.yourdomain.com",  # your CloudFront domain
            "querystring_auth": False,                # CloudFront handles access
            "default_acl": None,
            "file_overwrite": False,
        },
    },
    # ...
}
```

Use CloudFront **Origin Access Control (OAC)** so the bucket stays private and only CloudFront can read from it.

### 5.7 Separate folders (prefixes) for different file types

```python
# storage_backends.py
from storages.backends.s3 import S3Storage


class PublicMediaStorage(S3Storage):
    location = "public"
    default_acl = None
    querystring_auth = False
    file_overwrite = False


class PrivateMediaStorage(S3Storage):
    location = "private"
    default_acl = None
    querystring_auth = True
    file_overwrite = False
```

### 5.8 Using S3 for static files too (optional)

Often unnecessary; WhiteNoise or a CDN in front of your app is simpler. If you do want static files on S3:

```python
STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage", "OPTIONS": {"location": "media", "bucket_name": "..."}},
    "staticfiles": {"BACKEND": "storages.backends.s3.S3Storage", "OPTIONS": {"location": "static", "bucket_name": "..."}},
}
```

Then run `python manage.py collectstatic`.

---

## 6. Models, Forms, and Templates

These work the same for Cloudinary and S3.

### 6.1 Model with a safe `upload_to`

```python
# models.py
import uuid
from pathlib import Path
from django.db import models
from django.conf import settings


def user_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"users/{instance.owner_id}/{uuid.uuid4().hex}{ext}"


class Document(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=user_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

Using a UUID filename prevents collisions and avoids leaking or trusting user-provided names.

### 6.2 Validation (size and type)

```python
# validators.py
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

MAX_MB = 5


def validate_file_size(f):
    if f.size > MAX_MB * 1024 * 1024:
        raise ValidationError(f"File too large. Max size is {MAX_MB} MB.")


# models.py
file = models.FileField(
    upload_to=user_upload_path,
    validators=[
        validate_file_size,
        FileExtensionValidator(["pdf", "png", "jpg", "jpeg"]),
    ],
)
```

Extension checks are a first line of defense only. For stricter checks, inspect the actual content type (e.g. with `python-magic`).

### 6.3 Form and view

```python
# forms.py
from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "file"]
```

```python
# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import DocumentForm


@login_required
def upload_document(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.owner = request.user
            doc.save()
            return redirect("document_list")
    else:
        form = DocumentForm()
    return render(request, "documents/upload.html", {"form": form})
```

```html
<!-- documents/upload.html -->
<form method="post" enctype="multipart/form-data">
  {% csrf_token %} {{ form.as_p }}
  <button type="submit">Upload</button>
</form>
```

> `enctype="multipart/form-data"` and `request.FILES` are the two most commonly forgotten pieces.

### 6.4 Using different storages per field

Mix Cloudinary for images and S3 for documents in one project:

```python
# models.py
from django.db import models
from cloudinary_storage.storage import MediaCloudinaryStorage
from storages.backends.s3 import S3Storage


class Article(models.Model):
    cover = models.ImageField(upload_to="covers/", storage=MediaCloudinaryStorage())
    attachment = models.FileField(upload_to="attachments/", storage=S3Storage(bucket_name="my-docs-bucket"))
```

`storage` can also be a **callable** (Django 3.1+) that returns a storage instance, useful for switching per environment.

### 6.5 Displaying files

```html
{% if profile.avatar %}
<img src="{{ profile.avatar.url }}" alt="Avatar" width="120" />
{% endif %}

<a href="{{ document.file.url }}">Download {{ document.title }}</a>
```

For private S3 files, `.url` returns a temporary signed URL, so generate it at render time and don't store it.

---

## 7. Switching Storage by Environment

Use local disk in development and the cloud in production, controlled by an environment variable:

```python
# settings.py
import os

USE_CLOUD_STORAGE = os.getenv("USE_CLOUD_STORAGE", "False") == "True"
STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "s3")  # "s3" or "cloudinary"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

if USE_CLOUD_STORAGE and STORAGE_PROVIDER == "s3":
    INSTALLED_APPS += ["storages"]
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "region_name": os.getenv("AWS_S3_REGION_NAME"),
            "default_acl": None,
            "file_overwrite": False,
        },
    }

elif USE_CLOUD_STORAGE and STORAGE_PROVIDER == "cloudinary":
    INSTALLED_APPS = ["cloudinary_storage"] + INSTALLED_APPS + ["cloudinary"]
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
        "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
        "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
    }
    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}
```

For Cloudinary, `cloudinary_storage` must appear before `django.contrib.staticfiles` in `INSTALLED_APPS`. The snippet above prepends it to guarantee that, but if you maintain a hand-written list, keep that ordering.

Local development with S3-compatible tools (no AWS account needed):

```bash
docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
```

Then add `"endpoint_url": "http://localhost:9000"` to the S3 `OPTIONS`.

---

## 8. Direct Browser Uploads (Presigned URLs)

Uploading through Django means the file passes through your server, which wastes bandwidth and can hit request size or timeout limits on platforms like Heroku or serverless hosts. For big files, let the browser upload **directly to S3**.

### 8.1 S3 presigned POST

```python
# views.py
import uuid
import boto3
from botocore.config import Config
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


@login_required
def presign_upload(request):
    filename = request.GET.get("filename", "file")
    content_type = request.GET.get("content_type", "application/octet-stream")
    key = f"uploads/{request.user.id}/{uuid.uuid4().hex}-{filename}"

    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version="s3v4"),
    )
    presigned = s3.generate_presigned_post(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, 10 * 1024 * 1024],  # 1 byte to 10 MB
        ],
        ExpiresIn=300,
    )
    return JsonResponse({"upload": presigned, "key": key})
```

```javascript
// Browser code
async function uploadToS3(file) {
  const res = await fetch(
    `/presign/?filename=${encodeURIComponent(file.name)}&content_type=${encodeURIComponent(file.type)}`,
  );
  const { upload, key } = await res.json();

  const formData = new FormData();
  Object.entries(upload.fields).forEach(([k, v]) => formData.append(k, v));
  formData.append("file", file); // 'file' must be the LAST field

  const s3Response = await fetch(upload.url, {
    method: "POST",
    body: formData,
  });
  if (!s3Response.ok) throw new Error("Upload failed");
  return key; // send this key to your Django API to save on the model
}
```

Then save the `key` on your model. A `FileField` can store an existing key as its `name`. You need the S3 bucket's **CORS** configured ([5.5](#55-cors-needed-for-browser-side-uploads-or-fontsimages-used-by-js)).

### 8.2 Cloudinary unsigned or signed uploads

Cloudinary supports direct uploads through its **Upload Widget** or its upload endpoint with a **signed** request (generate the signature on your Django server with `cloudinary.utils.api_sign_request`) or an **upload preset**. Use signed uploads for anything beyond public demos, since unsigned presets let anyone who finds the preset name upload to your account.

---

## 9. Deleting and Cleaning Up Files

**Django does not delete the file when you delete a model instance or replace a file.** The row disappears and the cloud object stays, costing you storage.

### 9.1 Delete on model deletion

```python
# signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Document


@receiver(post_delete, sender=Document)
def delete_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
```

Register in `apps.py`:

```python
class DocumentsConfig(AppConfig):
    name = "documents"

    def ready(self):
        from . import signals  # noqa
```

### 9.2 Delete the old file when replacing

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=Document)
def delete_old_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Document.objects.get(pk=instance.pk).file
    except Document.DoesNotExist:
        return
    new = instance.file
    if old and old != new:
        old.delete(save=False)
```

Or use the maintained package `django-cleanup`, which does both automatically.

### 9.3 Lifecycle rules (S3)

In the bucket's **Management → Lifecycle rules**, you can expire temp uploads (e.g. under `tmp/`) after N days and move old files to cheaper storage classes.

---

## 10. Testing File Uploads

Never hit real cloud storage in tests. Use Django's in-memory storage (Django 4.2+):

```python
# settings.py (or a test settings module)
import sys

if "test" in sys.argv:
    STORAGES["default"] = {"BACKEND": "django.core.files.storage.InMemoryStorage"}
```

Or per test:

```python
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from .models import Document


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class UploadTest(TestCase):
    def test_upload(self):
        f = SimpleUploadedFile("hello.txt", b"hello world", content_type="text/plain")
        doc = Document.objects.create(owner=self.user, title="Hi", file=f)
        self.assertTrue(doc.file.name.endswith(".txt"))
```

For S3 integration tests, use [`moto`](https://github.com/getmoto/moto) to mock AWS, or MinIO/LocalStack.

---

## 11. Security Best Practices

- **Never commit credentials.** Use environment variables or your host's secrets manager. Rotate any key that was ever pushed to Git.
- **Least privilege.** The IAM user should only access the one bucket and only the actions it needs.
- **Prefer IAM roles** over long-lived keys when you run on AWS.
- **Keep buckets private** and serve via signed URLs or CloudFront OAC, unless the files are truly public.
- **Validate uploads:** limit size, extension, and content type. Never trust the client-supplied filename or MIME type.
- **Randomize filenames** (UUIDs) and namespace by user to avoid collisions and enumeration.
- **Don't serve user-uploaded HTML or SVG from your main domain** without sanitization, since they can run scripts (XSS). Serve them from a separate media domain.
- **Authorize access.** For private files, check in a view that the requesting user may see the file before handing out a signed URL.
- **Set upload limits** in Django (`DATA_UPLOAD_MAX_MEMORY_SIZE`, `FILE_UPLOAD_MAX_MEMORY_SIZE`) and at your reverse proxy (e.g. `client_max_body_size` in Nginx).
- **Cloudinary:** keep the API Secret server-side only. Use signed uploads from browsers.

---

## 12. Troubleshooting

| Symptom                                            | Likely cause and fix                                                                                                                  |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Files disappear after redeploy                     | Still using `FileSystemStorage` on an ephemeral disk. Check `STORAGES["default"]` in the production environment.                      |
| `NoCredentialsError`                               | AWS keys missing in the environment, or no IAM role attached.                                                                         |
| `AccessDenied` (403) on upload                     | IAM policy missing `s3:PutObject` or wrong bucket ARN (needs both `bucket` and `bucket/*`).                                           |
| `AccessControlListNotSupported`                    | Bucket has ACLs disabled. Set `default_acl: None`.                                                                                    |
| `SignatureDoesNotMatch` / `InvalidRequest`         | Wrong region or signature version. Set `region_name` and `signature_version: "s3v4"`.                                                 |
| Image URLs return 403                              | Bucket is private but `querystring_auth` is `False`. Either sign URLs or use CloudFront.                                              |
| Signed URLs expire too fast or too slowly          | Adjust `querystring_expire`.                                                                                                          |
| CORS error in browser                              | Add the origin and methods to the bucket's CORS config.                                                                               |
| Uploaded file name has odd suffix                  | `file_overwrite: False` appends a random string to avoid overwriting. Expected behavior.                                              |
| `ImportError: cloudinary_storage`                  | Package not installed, or `cloudinary_storage` missing from `INSTALLED_APPS`.                                                         |
| Cloudinary static files break                      | `cloudinary_storage` must be listed before `django.contrib.staticfiles`.                                                              |
| Cloudinary: PDF or ZIP fails to upload or download | Use `RawMediaCloudinaryStorage` for non-image files.                                                                                  |
| `Must supply cloud_name`                           | Credentials not loaded. Check env vars or `CLOUDINARY_STORAGE` / `CLOUDINARY_URL`.                                                    |
| `request.FILES` is empty                           | Form is missing `enctype="multipart/form-data"`.                                                                                      |
| `ValueError: ... no file associated`               | Accessing `.url` on an empty field. Guard with `{% if obj.file %}`.                                                                   |
| Upload times out or returns 413                    | Request too large for your proxy or host. Raise limits or use direct uploads ([section 8](#8-direct-browser-uploads-presigned-urls)). |

---

## 13. Production Checklist

**General**

- [ ] Production `STORAGES["default"]` is a cloud backend (not local disk)
- [ ] Credentials loaded from environment variables, never from Git
- [ ] `upload_to` uses UUID-based filenames
- [ ] Size and type validation on every upload field
- [ ] Old files deleted on replace and on model delete
- [ ] Tests use in-memory storage, not real cloud storage
- [ ] Reverse proxy and Django upload size limits configured
- [ ] Static files handled separately (WhiteNoise or CDN)

**S3**

- [ ] Bucket private, with Block Public Access on (unless intentionally public)
- [ ] Dedicated IAM user or role with least-privilege policy
- [ ] `default_acl: None`, `signature_version: "s3v4"`, region set
- [ ] CloudFront with Origin Access Control in front of the bucket
- [ ] CORS configured for browser uploads
- [ ] Lifecycle rules for temp files
- [ ] Versioning and/or backups enabled for important data
- [ ] Billing alerts set

**Cloudinary**

- [ ] `cloudinary_storage` listed before `django.contrib.staticfiles`
- [ ] API Secret kept server-side only
- [ ] Correct storage class per file type (media, video, raw)
- [ ] `quality="auto"` and `fetch_format="auto"` used on delivered images
- [ ] Signed uploads or restricted upload presets for browser uploads
- [ ] Usage and credit limits monitored in the dashboard

---

## Quick Reference

```python
# Cloudinary
STORAGES = {"default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}}

# S3
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {"bucket_name": "my-bucket", "region_name": "eu-central-1", "default_acl": None},
    }
}

# Install
pip install cloudinary django-cloudinary-storage      # Cloudinary
pip install django-storages boto3                      # S3

# Delete file from a model instance
instance.file.delete(save=False)

# Tests
STORAGES["default"] = {"BACKEND": "django.core.files.storage.InMemoryStorage"}
```
